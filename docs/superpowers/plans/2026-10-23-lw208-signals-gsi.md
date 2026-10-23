# LW-208 — Replace the unbounded `/api/signals` DynamoDB scan with a GSI

**Task:** LW-208 (governance revision 216, release-gate). Replace the full-table
`scan()` behind `/api/signals` that causes the measured ~6-7s hot-path latency.
**Status of record:** canonical `data.json` LW-208 still carries a stale
`title`/`description` ("Add scheduled pipeline, alarms, replay, and run audit")
from an old task slot; the authoritative scope is the NBA r216 + qa-explain-fix
response = "replace the unbounded /api/signals scan". Flag the stale title in the
completion handoff (cosmetic; status/deps already reconciled to `ready`/`[LW-635]`).

**Eng-review decisions (this session):**
- **D1 → A (GSI).** Add a GSI on `s3_key` (HASH) + `date` (RANGE). Chosen over the
  latest-projection-item approach. Tradeoff accepted: CDK change to the RETAIN
  signals table + infra test + moto changes + a real deploy (async GSI backfill)
  to verify — pulls LW-208 past a code-only merge into **deploy-gated** territory.
  Deploy requires Ian's explicit go. (decision `634b3f1f`)
- **D2 → A.** Add a `get_latest_signal(instrument)` single-instrument GSI query
  helper; `get_signal_detail` uses it instead of fetching all 19 and filtering.
- **D3 → A.** List path iterates the fixed 19 `INSTRUMENTS`, one
  `Query(s3_key=X, ScanIndexForward=false, Limit=1)` each, collects non-empty
  results. Output provably identical to today.

---

## Problem

`get_latest_signals()` (`apps/api/livewell/signals/dynamodb.py`) does an unbounded
paginated `table.scan()` of `livewell-signals-{env}`, reading **one item per
instrument per day of history** (~`19 × days`), then reduces in Python to the max
`date` per `s3_key`. Output is always ≤19 rows; the waste is reading all history to
find 19 "latest" rows. Latency grows daily → ~6-7s. The table has only a hash key
`signal_id = {s3_key}__{date}` — no sort key, no GSI — so a base-table `Query`
is impossible (every item is its own partition).

```
BEFORE (scan, O(19 × days)):
  /api/signals ─► get_latest_signals()
                    └─ table.scan()  ──► [EURUSD__2026-01-01, EURUSD__2026-01-02, …,   ~19×N items
                                          USDMXN__2026-10-23]
                    └─ Python reduce: group by s3_key, keep max(date)  ──► ≤19 rows

AFTER (GSI, O(19)):
  /api/signals ─► get_latest_signals()
                    └─ for s3_key in INSTRUMENTS (19):
                         GSI.Query(s3_key=X, ScanIndexForward=false, Limit=1) ──► 1 item
                    └─ collect non-empty  ──► ≤19 rows   (19 RCUs, history-independent)

  /api/signals/{instrument}/{strike} ─► get_latest_signal(s3_key)   # D2: single query, no 19-fetch
                    └─ GSI.Query(s3_key=X, ScanIndexForward=false, Limit=1) ──► latest date
                    └─ get_signal(s3_key, date)  # existing point get_item
```

## GSI design

- **Index name:** `by-instrument-date` (GSI1).
- **Partition key:** `s3_key` (STRING) — already on every item.
- **Sort key:** `date` (STRING, ISO `YYYY-MM-DD`, lexicographically sortable) —
  already on every item.
- **Projection:** `ALL`. Consumers read `strike_candidate`, `trend_bias`,
  `timing_slot`, `direction`, `signal_valid`, `score`, `reasoning`, etc.
  `KEYS_ONLY`/`INCLUDE` would force a second `get_item` per row. `ALL` is correct;
  cost is a slightly larger index (acceptable, PAY_PER_REQUEST).
- **Correctness note:** `Limit=1` + `ScanIndexForward=false` returns the true max
  `date` regardless of write order, so the backfill/replay out-of-order write case
  is handled natively by the index — no write-path invariant needed (this is the
  advantage that made D1→A self-maintaining).
- **String-numeric quirk preserved** (`signals-dynamodb-strings-vs-s3-floats`,
  confidence 9): GSI items carry the same string-typed numeric attributes; the
  transform layer already coerces. No change to write path or item shape.

## Changes

### 1. Infra — `infra/lib/livewell-stack.ts`
Add to the `signalsTable` definition:
```typescript
signalsTable.addGlobalSecondaryIndex({
  indexName: 'by-instrument-date',
  partitionKey: { name: 's3_key', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'date', type: dynamodb.AttributeType.STRING },
  projectionType: dynamodb.ProjectionType.ALL,
});
```
The pipeline IAM role already grants `dynamodb:Query` on `${arn}/index/*`
(livewell-stack.ts lines ~63-72) — no IAM change needed. The API's read role
must also allow `Query` on the index; verify the API Lambda/role policy includes
`dynamodb:Query` on `signals-table/index/*` (add if missing).

### 2. Read layer — `apps/api/livewell/signals/dynamodb.py`
- Add a private `_query_latest(table, s3_key) -> dict | None` that runs
  `table.query(IndexName="by-instrument-date", KeyConditionExpression=Key("s3_key").eq(s3_key), ScanIndexForward=False, Limit=1)`
  and returns `items[0]` or `None`. Wrap in the existing `ClientError` → log + `None`
  pattern.
- Rewrite `get_latest_signals()` to map `_query_latest` over `INSTRUMENTS`
  (import the 19-key list from `livewell.ingestion.constants`), skipping `None`.
  **Keep the signature and `list[dict]` return identical** — all four consumers
  (signals list, detail, dashboard, tracker) are then untouched.
- Add public `get_latest_signal(instrument: str) -> dict | None` =
  `_query_latest(_table(), instrument)` for the detail endpoint (D2).
- On `ClientError` for the whole list, keep returning `[]` (current behavior).

### 3. Router — `apps/api/routers/signals.py`
`get_signal_detail`: replace `records = get_latest_signals(); match = next(...)`
with `match = get_latest_signal(s3_key)`; `if match is None: 404`; then
`get_signal(s3_key, str(match["date"]))` as today. Import `get_latest_signal`.

### 4. Dashboard / tracker routers — no change
They call `get_latest_signals()` which keeps its contract. Verified both only
depend on the returned `list[dict]` shape.

## Tests

### Unit — `apps/api/tests/signals/test_dynamodb.py`
The current mocks use `table.scan.return_value`; switch to `table.query`:
- `_mock_table` → mock `.query` to return `{"Items": [...]}` keyed by the
  `s3_key` in the `KeyConditionExpression` (use `side_effect` to return the
  right instrument's latest, `[]` for unknown).
- Keep `test_get_latest_signals_returns_most_recent_per_instrument` (now asserts
  the query path returns one latest per instrument), `..._empty_table`,
  `..._returns_empty_on_client_error`.
- **Add** `test_get_latest_signal_single_instrument` (D2 helper: returns the one
  latest row for a given instrument, `None` when absent).
- **Add** `test_get_latest_signals_skips_instruments_with_no_signals` (D3: an
  instrument whose query returns `[]` is absent from the list — the exactly-19
  guarantee).
- Keep the string-typed `score: "0.71"` sample items (quirk coverage).

### Integration (moto) — `apps/api/tests/test_signals.py`
- `signals_table` fixture + `test_get_signals_returns_empty_list_when_no_data`:
  add the GSI and the `date` AttributeDefinition to **both** `create_table`
  calls, or moto `Query` on the index fails:
  ```python
  KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
  AttributeDefinitions=[
      {"AttributeName": "signal_id", "AttributeType": "S"},
      {"AttributeName": "s3_key", "AttributeType": "S"},
      {"AttributeName": "date", "AttributeType": "S"},
  ],
  GlobalSecondaryIndexes=[{
      "IndexName": "by-instrument-date",
      "KeySchema": [
          {"AttributeName": "s3_key", "KeyType": "HASH"},
          {"AttributeName": "date", "KeyType": "RANGE"},
      ],
      "Projection": {"ProjectionType": "ALL"},
  }],
  ```
- **Add** an integration test that seeds two dates for one instrument and asserts
  the list + detail endpoints return the newer one (end-to-end "latest" via the
  index, covering the out-of-order-write guarantee).
- Existing endpoint tests (`test_get_signals_returns_dynamodb_records`,
  `test_signal_valid_false_maps_to_watch_status`, `test_get_signal_detail_found`,
  `test_get_signal_detail_not_found`) should pass unchanged once the fixture has
  the GSI.

### Infra — `infra/test/livewell-stack.test.ts`
Update the signals-table assertion (lines ~77-85) to expect the new GSI
(`GlobalSecondaryIndexes` with `by-instrument-date`, `s3_key`/`date` key schema,
`ALL` projection) and the two added attribute definitions.

## Verification

- `cd apps/api && AWS_DEFAULT_REGION=us-west-1 uv run pytest` — all green (256+ tests).
- `cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy .`
- `cd infra && npm test` — CDK assertion updated and green.
- `cd apps/web && npm run build && npm test` — unaffected, confirm still green.
- `./scripts/quality.sh` — all seven arms green from zero.
- **Local behavior:** moto integration tests prove the index returns the same
  ≤19-row output as the scan did.

## Deploy gate (explicit — NOT part of the code merge)

The GSI add is a CDK change to a **RETAIN** production table. It requires:
1. `cdk diff` reviewed (adds GSI only; no destructive change to the base table).
2. An actual `cdk deploy` — GSI backfill over existing items is **async**; the
   index is not queryable until backfill completes.
3. Post-deploy verification: `GET /api/signals` returns ≤19 rows in <1s, and
   `GET /api/signals/{instrument}/{strike}` resolves. If the API is hit before
   GSI backfill finishes, queries return partial/empty — verify backfill
   `IndexStatus: ACTIVE` before trusting results.

**Deploy happens only on Ian's explicit request.** The code + tests merge first
and are locally verified via moto; the deploy is a separate, gated step.

## NOT in scope

- Concurrency for the 19 queries (`ThreadPoolExecutor`/async) — deferred; 19
  serial `Limit=1` reads are already sub-100ms.
- Numeric confidence-interval modeling / source-level reason structuring
  (deferred LW-207 follow-ups, per NBA r216).
- Fixing the stale LW-208 `title`/`description` field — flag in handoff, not a
  code change.
- Reopening congressional work (closed, ADR-0002).

---

## GSTACK REVIEW REPORT

**Skill:** /plan-eng-review · **Target:** LW-208 (governance task, no prior branch diff) · **Date:** 2026-10-23 · **Reviewer model:** claude

### Scope outcome
Bounded performance refactor of one endpoint family. Does NOT trip the complexity
smell (1 infra file + 1 read-layer file + 1 router + 3 test files; 0 new
classes/services). Scope held; no reduction needed.

### Decisions (all user-approved)
| ID | Decision | Chosen | Recommended | Confidence |
|----|----------|--------|-------------|------------|
| D1 | Access pattern | **A** GSI (`s3_key`+`date`) | B projection-item | 8/10 |
| D2 | Detail endpoint | **A** single-instrument `get_latest_signal()` helper | A | 9/10 |
| D3 | List query shape | **A** 19 bounded `Query`+`Limit=1` over `INSTRUMENTS` | A | 9/10 |

D1: user chose A over the recommended B — accepts the deploy gate in exchange for
a self-maintaining index + future last-N-history queries. Logged `634b3f1f`.

### Findings by section
1. **Architecture** — 1 finding (D1 access pattern). Base table is hash-only on
   `signal_id`; GSI is the canonical latest-per-partition fix [Layer 1]. GSI
   handles out-of-order replay writes natively (sorts by `date` range key).
2. **Code quality** — 1 finding (D2). `get_signal_detail` paid a full 19-fetch to
   resolve one instrument's date; now a single GSI query. DRY: one private
   `_query_latest` builder, two public entry points (`get_latest_signals` maps it
   over 19; `get_latest_signal` calls it once).
3. **Tests** — 1 finding (D3) + coverage plan. Unit mocks move `scan`→`query`;
   moto fixtures gain the GSI + `date`/`s3_key` attr defs in two spots; new tests
   for single-instrument helper, missing-instrument skip, and out-of-order "latest".
   Infra assertion test updated for the GSI.
4. **Performance** — no open decision. Read bounded to 19 RCUs, history-independent
   (~6-7s → sub-100ms). GSI projection `ALL` avoids a second round-trip per row.
   Concurrency deferred.

### Prior learnings applied
- `signals-dynamodb-strings-vs-s3-floats` (9/10) — GSI items keep string-typed
  numerics; transform layer already coerces; no write-path change. Verified.
- `verify-deps-before-starting-activated-task` (9/10) — confirmed LW-208 deps
  reconciled to `[LW-635]` at rev 216 before planning. Noted stale `title` field
  remains (cosmetic).

### Suppressed findings (confidence <7)
None.

### Risk / watch
- **Deploy-gated:** GSI add is a CDK change to a RETAIN table with async backfill;
  index not queryable until `ACTIVE`. Merge code first (moto-verified), deploy
  separately on explicit request, verify backfill before trusting live results.
- Confirm the **API read role** grants `dynamodb:Query` on
  `signals-table/index/*` (pipeline role already does; API role must too).

### Status
**DONE** — plan written, all four sections reviewed, three decisions approved and
logged. Ready for implementation on explicit go. No code changed during review.
