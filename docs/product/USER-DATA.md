## Multiple tabular formats — October16

CSV, TSV, Excel .xlsx, JSON and JSONL are accepted through the guided product. [Formats, worksheet selection, exact conversion and limits](FILE-IMPORTS.md). Existing domain contracts and result/approval checks remain applicable; PDFs/images are unsupported. Earlier CSV-specific implementation descriptions below remain historical context for the normalized analysis engine.

# QueryPilot: work with your own data

The public `/uploads` workspace accepts visitor-owned CSVs and returns source-derived results. Existing sample investigations remain separate. No provider keys are configured in the public deployment: these are explicitly reviewed contract workflows, not live language interpretation or measured general-purpose agent accuracy.

```mermaid
flowchart LR
    A[Visitor CSV] --> B[Bounded parse and profile]
    B --> C[Review column and business contract]
    C --> D[Execute source-derived workflow]
    D --> E[Independent verification]
    E --> F[Review results and export]
```

## Business contract

Select sum, count or average, an optional grouping column and optional exact-match filter. Sum/average require an explicitly mapped numeric measure; count does not. Values are bounded plain decimals with up to six fractional digits. Included missing or malformed numeric values refuse the result rather than silently disappearing. An empty filter result is withheld. All source rows, including duplicates, count unless the user has cleaned them before upload.

In-memory SQLite executes a generated aggregate over normalized `segment` and integer `value_micro` columns. Independent Python Decimal aggregation reconciles group sums and counts; averages use the verified sum divided by its actual row count, never averages of group averages. JSON/CSV preserve decimal strings; repeating averages use a documented 38-digit Decimal context. SQL, source hash, normalization bindings, selected contract and verification accompany each result. No shared sample warehouse, login account, saved investigation history or live model is used. The standalone `/uploads` workspace is served from `frontend/public/uploads` (copied into the Vite build); the existing React sample app links to it.

## Data handling and limits

- UTF-8 comma-separated CSV with one header row; maximum 400,000 UTF-8 bytes, 60 columns, 120 characters per header and 2,048 characters per cell. Case-insensitive duplicate headers, ragged records, invalid control characters and empty files are refused.
- At most 5000 rows per analysis; at most 100 aggregate result groups. Each numeric source value is at most 100 million in magnitude; RelayOps also enforces its existing ten-million action bound.
- The browser reads a selected file and transmits its CSV text inside bounded JSON. An outer ASGI middleware counts actual streamed bytes before JSON decoding, rejects bodies over 1 MB and limits body reception to 15 seconds. No multipart package is necessary.
- Parsing/analysis run in FastAPI's synchronous handler thread pool, outside the event loop. This does not provide global admission control across serverless instances.
- Processing uses memory and, for operational worlds, automatically cleaned temporary scratch. Original rows/results are not deliberately persisted in shared history, application logs, browser local storage or session storage by default. Explicit device save uses IndexedDB, and configured cloud save requires separate consent. Unsaved browser files/results disappear on reload or Clear. Explicit consent now enables immutable IndexedDB snapshots and portable backups; see [product storage](PRODUCT-WORKSPACE.md). Hosting providers may retain request metadata; this is not a confidential-data hosting certification.
- User content is rendered with text nodes, never HTML. CSV exports neutralize formula-like text while preserving typed numeric negatives. Filenames never become server filesystem paths. No uploaded code, external URLs, extensions or arbitrary SQL are executed.
- Live generation, tenant identity, persistent connector credentials, durable uploaded datasets, asynchronous large-file jobs and monitored customer execution are separate release gates.

The app's limits remain below [Vercel's request/response payload limit](https://vercel.com/docs/functions/limitations). Larger exports need a separately designed direct-object-upload and durable-worker flow, not a larger JSON request.

## Endpoints

`GET /api/uploads/capabilities`, `GET /api/uploads/template`, `POST /api/uploads/profile`, `POST /api/uploads/analyze`. The narrow public upload allowlist does not enable legacy state-changing operator endpoints. Every analysis request includes the original CSV and explicit mapping/options. API responses are not cached.

See the implementation's `uploads` package and `backend/tests/api/test_uploads.py` for independently authored expected values, changed-input, validation and isolation regressions. Local/deployed verification is recorded in the project handoff after it actually runs.
