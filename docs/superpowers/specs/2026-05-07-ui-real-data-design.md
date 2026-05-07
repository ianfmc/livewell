# UI Real Data Wiring — Design Spec

**Goal:** Replace MSW mock data with real FastAPI endpoints backed by DynamoDB, deploying the API as a Lambda Function URL.

**Approach:** Deploy FastAPI first (Lambda Function URL via CDK), then wire all 8 pages. Transformation from raw DynamoDB records to typed API responses happens in a Python service layer — not in the frontend.

---

## 1. API Deployment

FastAPI is packaged as a Docker container image and deployed as a Lambda `DockerImageFunction` with a Function URL (no API Gateway needed).

### New files

- `apps/api/Dockerfile.api` — runs `uvicorn main:app --host 0.0.0.0 --port 8000`, installs dependencies via `uv`
- `apps/api/livewell/signals/` — new package for DynamoDB reads and transformation (extracted from routers)

### Modified files

- `apps/api/main.py` — add Mangum ASGI handler, env-based CORS origins, `GET /health` endpoint
- `infra/lib/livewell-stack.ts` — add API Lambda, Function URL, ECR image build, IAM role

### CDK additions (`infra/lib/livewell-stack.ts`)

```typescript
// DockerImageFunction for FastAPI
const apiLambda = new DockerImageFunction(this, 'ApiLambda', {
  code: DockerImageCode.fromImageAsset('../apps/api', { file: 'Dockerfile.api' }),
  architecture: Architecture.ARM_64,
  memorySize: 512,
  timeout: Duration.seconds(30),
  environment: {
    LIVEWELL_ENV: env,
    LIVEWELL_BUCKET: dataBucket.bucketName,
    CORS_ORIGINS: props.corsOrigins,  // passed from context
  },
});

// Grant read access to DynamoDB tables
signalsTable.grantReadData(apiLambda);
modelRegistryTable.grantReadData(apiLambda);

// Public Function URL (no auth — personal tool)
const apiUrl = apiLambda.addFunctionUrl({
  authType: FunctionUrlAuthType.NONE,
  cors: { allowedOrigins: ['*'] },
});

new CfnOutput(this, 'ApiUrl', { value: apiUrl.url });
```

### CORS strategy

`main.py` reads `CORS_ORIGINS` env var (comma-separated list). Lambda sets it to the React app origin. Local dev keeps the existing hardcoded localhost list. No origins hardcoded in code.

```python
origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], ...)
```

### Health endpoint

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

### Mangum handler

```python
from mangum import Mangum
handler = Mangum(app)  # Lambda entrypoint
```

---

## 2. Data Transformation Layer

A new `apps/api/livewell/signals/` package contains all logic for reading signals from DynamoDB and mapping them to API response schemas. Routers become thin orchestrators.

### File structure

```
apps/api/livewell/signals/
  __init__.py
  dynamodb.py     — reads from livewell-signals-{env} table
  transform.py    — pure mapping functions, no I/O
```

### `dynamodb.py`

```python
def get_latest_signals() -> list[dict]:
    """Scan signals table, return one record per instrument (most recent by date)."""

def get_signal(instrument: str, date: str) -> dict | None:
    """Fetch a single signal record by instrument and date."""
```

### `transform.py` — mapping rules

**`to_contract_card(record: dict) -> ContractCard`**

| DynamoDB field | ContractCard field |
|---|---|
| `s3_key` | `instrument` (display name via `INSTRUMENTS` map) |
| `strike_candidate` | `strike` |
| `timing_slot` | `expiry` |
| `date` | used to build `signalId` |
| `recommendation = "Take"` → "Open", `"Watch"` → "Review", `"Pass"` → "Closed" | `status` ("Open" / "Review" / "Closed") |

**`to_contract_detail(record: dict) -> ContractDetail`**

All `ContractCard` fields plus:

| Logic | Output field |
|---|---|
| `score ≥ 0.65` AND `signal_valid=True` AND `direction ≠ "none"` | `recommendation: "Take"` |
| `score 0.55–0.65` OR `signal_valid=False` | `recommendation: "Watch"` |
| `score < 0.55` OR `direction = "none"` | `recommendation: "Pass"` |
| `score ≥ 0.70` | `confidence: "High"` |
| `score 0.58–0.70` | `confidence: "Medium"` |
| `score < 0.58` | `confidence: "Low"` |
| `score × 2 − 1` | `edge` |
| `trend_bias` (passed through) | `regime` |
| `timing_risk = "high"` | `noTradeFlag: True` |
| parsed `reasoning` JSON | `reasonCodes: list[ReasonCode]` |
| `score` | `modelProbability` (None if null — pre-model signals) |

Null-safe: if `score` is null (signal written before model was registered), `recommendation` defaults to `"Watch"` and `modelProbability` is `None`.

**`to_model_health(registry_record: dict) -> ModelHealth`**

Reads the active model from `livewell-model-registry-{env}` via `get_active_model()`. Maps `trained_at`, `win_rate`, and `version` to the `ModelHealth` schema.

**Dashboard aggregation (`routers/dashboard.py`)**

```python
signals = get_latest_signals()
cards = [to_contract_card(s) for s in signals]
total = len(cards)
passing = sum(1 for s in signals if float(s.get("score") or 0) >= 0.65)
review = sum(1 for s in signals if 0.55 <= float(s.get("score") or 0) < 0.65)
top = sorted(signals, key=lambda s: float(s.get("score") or 0), reverse=True)[:3]
```

---

## 3. Frontend Wiring

### MSW made opt-in

`apps/web/src/main.tsx` — MSW only starts when `VITE_ENABLE_MOCKS=true`:

```typescript
if (import.meta.env.VITE_ENABLE_MOCKS === "true") {
  const { worker } = await import("./mocks/browser");
  await worker.start();
}
```

### API base URL

New file `apps/web/src/lib/api.ts`:

```typescript
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
// Empty string → relative URLs → Vite proxy handles local dev
// Lambda URL → absolute → direct to AWS in prod
```

All hooks updated to use `${API_BASE}/api/...`.

### Env files

| File | Contents |
|---|---|
| `.env.local` | `VITE_ENABLE_MOCKS=true` (local dev with mocks) |
| `.env.development` | `VITE_API_BASE_URL=` (empty — Vite proxy) |
| `.env.production` | `VITE_API_BASE_URL=https://<lambda-url>`, `VITE_ENABLE_MOCKS=false` |

`.env.local` is gitignored. `.env.production` is committed (URL is not a secret).

### Pages and data sources

| Page | Data source | Status |
|---|---|---|
| DailySignals | DynamoDB signals → ContractCard list | real data |
| ContractDetail | DynamoDB signal by instrument + date | real data |
| Dashboard | Aggregated from signals + model registry | real data |
| ModelHealth | Model registry table | real data |
| SignalTracker | Historical signals from DynamoDB | real data |
| OptionsAdvisor | SSE explain endpoint (already wired) | real data |
| BacktestResults | No pipeline yet — returns stub | stub |
| HowItWorks | Static content | static |

---

## 4. Testing

### Backend

| Test file | What it covers |
|---|---|
| `tests/signals/test_transform.py` | All threshold boundaries — Take/Watch/Pass, High/Medium/Low confidence, edge calculation, noTradeFlag, reasonCodes parsing, null score handling |
| `tests/signals/test_dynamodb.py` | DynamoDB read functions with mocked boto3 |
| `tests/routers/test_signals.py` | GET /api/signals and GET /api/signals/{instrument}/{strike} via httpx, mocked DynamoDB |
| `tests/routers/test_dashboard.py` | GET /api/dashboard aggregation logic |
| `tests/test_health.py` | GET /health returns 200 |

### Deployment smoke test

After `cdk deploy`:
```bash
curl https://<lambda-url>/health          # → {"status":"ok"}
curl https://<lambda-url>/api/signals     # → non-empty list with real scores
```

### Cold starts

Lambda cold starts with scikit-learn take 4–6s. The UI already shows loading states — no special handling needed for MVP. If latency becomes a problem, an EventBridge rule pinging the function every 5 minutes keeps it warm.

---

## Out of scope

- Authentication / authorization
- Custom domain for the Lambda URL
- BacktestResults real data (no backtest pipeline exists yet)
- API versioning (`/api/v1/` prefix)
- Response envelopes (`{ status, data, metadata }` wrapper)
