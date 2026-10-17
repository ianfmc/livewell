# LW-104 — Canonical Disclosure Schema & Source-Document Lineage

- **Checklist:** LW-104 (release gate). Discovery-contract item of LW-W1.
- **Status:** DRAFT design — for Ian's review. Design document only.
- **Date:** 2026-10-16
- **Depends on (done):** LW-101 (ADR-0001), LW-103 (access/terms), LW-635.
- **Related:** `docs/adr/0001-congressional-trading-signal.md`,
  `docs/research/congressional-disclosure-access.md`,
  `docs/research/congressional-disclosure-limitations.md`,
  `docs/designs/congressional-trading-signal.md`.
  Downstream consumers: LW-105 (asset resolution), LW-107 (leakage-safe clock),
  LW-111 (sample fixtures + normalization checks), LW-108/LW-206 (join + ablation).

> **Scope guardrail (governance, rev 183).** This is design + invented-fixtures
> work only. It does **not** acquire real disclosures and does **not** authorize
> production integration. LW-110 (access gate) is blocked; LW-112/LW-113 are
> deferred. Every example record in this document is **invented and clearly
> labeled**; none is derived from a real filing.

---

## 1. Purpose

Define the single canonical shape every congressional-disclosure **transaction
record** takes once normalized, and the **lineage** that ties each record back to
the exact source document it came from. This schema is the contract that
LW-105/107/111 and the eventual ablation all build on. It is a *data-handling*
contract, not evidence of predictive value (that is LW-206's job).

The schema must satisfy the LW-104 acceptance criterion: preserve **document
lineage, retrieval and public-availability times, filing and transaction dates,
owner, asset text, type, and value range.**

## 2. Grain and scope

- **Grain:** one row per **disclosed transaction** (one PTR line item). A single
  filing (PTR document) typically contains several transactions → several rows
  sharing one `filing_id`/lineage block.
- **Coverage (v1):** House Clerk FD + Senate eFD Periodic Transaction Reports
  (PTRs) only. Executive-branch (OGE) is out of scope (LW-D02).
- **Storage:** analytical S3 layer as a normalized table (Parquet/CSV under e.g.
  `curated/congress/`), consistent with the settled S3-analytical /
  DynamoDB-operational split. No schema change to existing stores.

## 3. Design principles (from LW-102 limitations)

1. **Three clocks are first-class and never conflated.** transaction date,
   filing-availability (publication) date, and LIVEWELL observation date are
   stored as three separate fields. LW-107 keys on filing-availability; nothing
   downstream may use `transaction_date` as the point-in-time clock.
2. **Preserve source text alongside any inference.** The raw asset text and raw
   amount text are kept verbatim; resolved/parsed values live in separate fields
   so a parsing change never destroys the original.
3. **Value is a range, never a point.** Amounts are brackets; store the bracket
   bounds, not a fabricated exact figure. Midpoints, if ever used, are derived
   downstream and clearly labeled.
4. **Lineage is mandatory.** Every row can be traced to its source document
   (source system, document id, URL/locator, retrieval time, content hash).
5. **Amendments and duplicates are representable** without back-dating a
   correction into a period before it was public (LW-201/202 handle the logic;
   the schema just has to carry the fields).
6. **Low-confidence is visible, not silent.** Asset resolution confidence and a
   review-queue flag are part of the record (populated by LW-105).

## 4. Canonical schema

Field table. Types are logical; `date` = ISO-8601 date, `timestamp` = ISO-8601
UTC datetime. "Source" = where the value originates.

### 4.1 Identity & lineage (satisfies "document lineage")

| Field | Type | Req | Description | Source |
|---|---|---|---|---|
| `record_id` | string | yes | Stable surrogate key for this transaction row. Deterministic hash of (`source_system`, `document_id`, `line_index`). | derived |
| `source_system` | enum(`house_fd`,`senate_efd`) | yes | Which official system published the document. | lineage |
| `document_id` | string | yes | Native document identifier (House DocID; Senate report id). | source |
| `filing_id` | string | yes | Groups all transactions from one PTR document. Usually = `document_id`. | derived |
| `line_index` | int | yes | 0-based position of the transaction within its document. | derived |
| `source_url` | string | yes | Canonical locator of the source document (PDF/HTML/JSON record). | lineage |
| `source_format` | enum(`pdf`,`html`,`json`,`xml`,`txt`) | yes | Format the record was extracted from. | lineage |
| `content_hash` | string | yes | SHA-256 of the retrieved source document bytes — tamper/version check + dedupe. | derived |
| `extractor` | string | yes | Tool + pinned revision that produced the row (e.g. `quantgress@<rev>`). | lineage |
| `schema_version` | string | yes | Version of *this* canonical schema the row conforms to (e.g. `1.0`). | fixed |

### 4.2 Timing — three clocks (satisfies "retrieval + public-availability times, filing + transaction dates")

| Field | Type | Req | Description |
|---|---|---|---|
| `transaction_date` | date | yes | Clock 1 — when the member traded. **Never** used as the point-in-time clock. |
| `transaction_date_is_range` | bool | no | True if the source gave a transaction date range rather than a single day. |
| `filing_date` | date | yes | Date the PTR was filed with the chamber. |
| `public_availability_at` | timestamp | yes | Clock 2 — first moment the document was publicly retrievable. The LW-107 point-in-time clock. If only a date is known, store as that date at 00:00Z and set `public_availability_precision`. |
| `public_availability_precision` | enum(`timestamp`,`date`) | yes | Whether clock 2 is known to the second or only to the day. |
| `observed_at` | timestamp | yes | Clock 3 — when LIVEWELL's ingest first retrieved/normalized this record. ≥ `public_availability_at`. |

### 4.3 Filer / owner (satisfies "owner")

| Field | Type | Req | Description |
|---|---|---|---|
| `filer_name` | string | yes | Reporting member's name as published. |
| `filer_chamber` | enum(`house`,`senate`) | yes | Chamber. |
| `filer_id` | string | no | Stable filer identifier if resolvable (e.g. bioguide); null if unresolved. |
| `owner` | enum(`self`,`spouse`,`dependent`,`joint`,`unknown`) | yes | Account owner as disclosed (the PTR "Owner" column: SP/DC/JT/etc. normalized). |

### 4.4 Asset (satisfies "asset text, type")

| Field | Type | Req | Description |
|---|---|---|---|
| `asset_text_raw` | string | yes | Verbatim free-text asset description from the source. Never overwritten. |
| `asset_ticker_raw` | string | no | Ticker exactly as it appeared in the source, if any. |
| `asset_type` | enum(`stock`,`etf`,`option`,`bond`,`fund`,`crypto`,`other`,`unknown`) | yes | Disclosed instrument class, normalized. `unknown` when unparseable. |
| `resolved_ticker` | string | no | Ticker after LW-105 resolution; null until resolved. |
| `resolution_confidence` | float [0,1] | no | LW-105 confidence; null until resolved. |
| `needs_manual_review` | bool | yes | True when resolution is low-confidence/ambiguous (LW-105/203). Default false only when confidently resolved or trivially exact. |

### 4.5 Transaction type & value (satisfies "type, value range")

| Field | Type | Req | Description |
|---|---|---|---|
| `tx_type` | enum(`purchase`,`sale`,`sale_partial`,`sale_full`,`exchange`,`unknown`) | yes | Transaction type normalized from the PTR type column (P / S / S(partial) / E). |
| `amount_range_raw` | string | yes | Verbatim amount bracket text (e.g. `"$1,001 - $15,000"`). Never overwritten. |
| `amount_min` | decimal | yes | Lower bound of the disclosed bracket, parsed. |
| `amount_max` | decimal | yes | Upper bound of the disclosed bracket, parsed. Equal to `amount_min` only if the source genuinely gives an exact figure (rare). |
| `amount_currency` | string | yes | Currency of the bracket; `USD` for House/Senate PTRs. |

### 4.6 Amendment / supersedence (representability only; logic is LW-201/202)

| Field | Type | Req | Description |
|---|---|---|---|
| `is_amendment` | bool | yes | True if the source document is an amendment of a prior filing. |
| `amends_document_id` | string | no | `document_id` of the filing this one amends; null otherwise. |
| `supersedes_record_id` | string | no | `record_id` this row replaces, when a correction maps 1:1 to a prior row. Resolution of supersedence is downstream; the field only has to exist. |

## 5. Lineage model (narrative)

Each **source document** (one PTR) retrieved from an official system produces a
**lineage block** — `source_system`, `document_id`, `source_url`,
`source_format`, `content_hash`, `extractor`, `public_availability_at`,
`observed_at` — shared by every transaction row extracted from it. The document
→ transaction relationship is one-to-many via `filing_id` + `line_index`.
`content_hash` lets ingest detect when a re-retrieved document changed (amendment
or re-publication) and lets dedupe drop byte-identical re-pulls. This is what the
acceptance criterion means by "preserve document lineage": from any single row
you can name the exact document, where it came from, in what format, when it
became public, when we saw it, and the tool revision that parsed it.

## 6. Invented example record (NOT real data)

> Fabricated for illustration. Filer, dates, and asset are invented. No real
> disclosure was accessed to produce this.

```json
{
  "record_id": "sha256:fe9c...a1",
  "source_system": "house_fd",
  "document_id": "DEMO-20099999",
  "filing_id": "DEMO-20099999",
  "line_index": 0,
  "source_url": "https://example.invalid/demo/DEMO-20099999.pdf",
  "source_format": "pdf",
  "content_hash": "sha256:4b1d...9f",
  "extractor": "quantgress@<pinned-rev>",
  "schema_version": "1.0",

  "transaction_date": "2026-02-03",
  "transaction_date_is_range": false,
  "filing_date": "2026-03-10",
  "public_availability_at": "2026-03-11T00:00:00Z",
  "public_availability_precision": "date",
  "observed_at": "2026-03-12T06:15:00Z",

  "filer_name": "Jane Q. Example",
  "filer_chamber": "house",
  "filer_id": null,
  "owner": "self",

  "asset_text_raw": "DemoCorp Class A Common Stock (DEMO)",
  "asset_ticker_raw": "DEMO",
  "asset_type": "stock",
  "resolved_ticker": null,
  "resolution_confidence": null,
  "needs_manual_review": true,

  "tx_type": "purchase",
  "amount_range_raw": "$1,001 - $15,000",
  "amount_min": 1001,
  "amount_max": 15000,
  "amount_currency": "USD",

  "is_amendment": false,
  "amends_document_id": null,
  "supersedes_record_id": null
}
```

## 7. Mapping to real source formats (from LW-103, no acquisition performed)

Documents how known source fields *would* map — reference only; no data pulled.

- **House Clerk FD:** the annual ZIP (`<year>FD.txt` tab-delimited + `<year>FD.xml`)
  supplies filing **metadata/DocIDs** (→ `document_id`, `filing_date`,
  `filer_name`, `filer_chamber=house`), not transaction rows. Transaction fields
  (`transaction_date`, `tx_type`, `asset_text_raw`, `amount_range_raw`) come from
  the individual PTR PDF (`FilingType=P`) → `source_format=pdf`. Scanned PDFs may
  be OCR-only; those rows carry lower-confidence text and `needs_manual_review`.
- **Senate eFD:** search metadata JSON (`/search/report/data/`) → document
  identity + `filer_name`/`filer_chamber=senate`; the electronic PTR detail page
  (HTML table) → transaction rows (`source_format=html`). Paper/image reports need
  separate handling and may be unavailable.
- **`public_availability_at`** is sourced from the system's published/retrieval
  signal, falling back to the retrieval date with `precision=date` when no
  explicit publish timestamp exists. This is the field LW-107 keys on, so its
  provenance is recorded per row.

## 8. Open questions for LW-105 / LW-107 (not resolved here)

- Exact confidence scale + manual-review threshold for `resolution_confidence` /
  `needs_manual_review` — **LW-105**.
- Precise rule when only `filing_date` is known and no publish timestamp exists:
  does LW-107 treat `public_availability_at = filing_date` or `filing_date + N`?
  Schema supports either via `public_availability_precision`; the **policy** is
  LW-107's to set.
- Supersedence resolution algorithm (which amendment wins, how periods are kept
  point-in-time correct) — **LW-201/202**; schema only carries the fields.

## 9. Acceptance-criterion checklist (LW-104)

| Required element | Field(s) |
|---|---|
| document lineage | §4.1 full block + §5 |
| retrieval time | `observed_at` |
| public-availability time | `public_availability_at` (+ precision) |
| filing date | `filing_date` |
| transaction date | `transaction_date` |
| owner | `owner` (+ `filer_name`/`filer_chamber`/`filer_id`) |
| asset text | `asset_text_raw` (+ `asset_ticker_raw`) |
| type | `asset_type`, `tx_type` |
| value range | `amount_range_raw`, `amount_min`, `amount_max`, `amount_currency` |

All nine required elements are covered.
