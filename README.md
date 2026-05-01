# Markr

## Quick start

```bash
docker compose up --build
```

POST one batch:

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<XML
<mcq-test-results>
  <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
    <first-name>Jane</first-name>
    <last-name>Austen</last-name>
    <student-number>521585128</student-number>
    <test-id>1234</test-id>
    <summary-marks available="20" obtained="13" />
  </mcq-test-result>
</mcq-test-results>
XML
```

GET aggregate stats:

```bash
curl -sS http://localhost:4567/results/1234/aggregate
```

Expected shape for the example above:

```json
{"mean":65.0,"stddev":0.0,"min":65.0,"max":65.0,"p25":65.0,"p50":65.0,"p75":65.0,"count":1}
```

## Assumptions

Safe because the import contract treats each request as the atomic unit.
- One POST = one complete XML batch. Scanner sends a request only after the body is fully assembled (not HTTP chunked-transfer streaming).

Safe because the prototype still has defensive caps for outliers.
- Realistic batch sizes are tens to low hundreds of records. Five-figure batches are not the normal workflow; the 10 MiB / 10,000-record caps are defensive backstops.

Safe because the customer scope implies broad deployment.
- Multi-scanner concurrency exists. Inferred from "every school system in Europe & North America"; not stated in brief.

Safe because these are the fields required to persist and aggregate scores.
- Required fields are `student-number`, `test-id`, `summary-marks/@available` (>0), `summary-marks/@obtained`. Other fields (`first-name`, `last-name`, `scanned-on`) are tolerated when present, ignored when absent or unparseable.

Safe because the brief tells us to trust it for now.
- `summary-marks` is trusted; `<answer>` elements are ignored. Per brief.

Safe because the brief says extra fields should not concern this service.
- Unknown XML elements are ignored without error. Per brief.

Safe because the brief warns other XML document kinds exist.
- Documents whose root element is not `<mcq-test-results>` are rejected. Per brief's "other kinds of XML"; namespaced roots fall into this category.

Safe because percentages require a positive denominator and impossible scores should not persist.
- `available > 0` and `obtained <= available` are enforced as validation rules and as DB CHECK constraints.

## Decisions & trade-offs

The prototype is a single FastAPI service rather than two services. Separate write/read engines give ingest-vs-aggregate pool isolation without deployment overhead. A later split remains local to the module and repository boundaries.

Imports are synchronous through COMMIT, not fire-and-forget. That preserves the brief's "reject the entire document" contract and makes scanner retries deterministic.

XML is parsed as a hardened DOM with `defusedxml`, not streamed. The 10 MiB body cap makes DOM safe and keeps validation simple.

The service trusts `<summary-marks>` and ignores `<answer>` elements because the brief explicitly directs that trade-off.

Duplicate records inside one request are reduced in app code before writing, using the highest obtained and available marks per `(test_id, student_number)`. Cross-request duplicates are handled by database UPSERT.

An empty batch returns 422 `empty_batch`. The brief is silent on zero-record documents; rejecting loudly is safer than accepting a silent no-op.

Aggregate stats are not rounded in application code. PostgreSQL returns the numeric result and the response preserves that value.

## Excluded (deliberately)

| Item | Reason |
|---|---|
| Authentication / TLS | brief explicitly waves off |
| Use of `<answer>` elements | brief: trust `<summary-marks>` |
| Real-time dashboards | brief asks for written design only |
| Streaming XML parser | DOM is safe under 10 MiB cap; sidesteps element-order question |
| 100% test coverage | brief explicitly de-prioritises |
| Pub-sub / event queue between ingest and DB | incompatible with "reject the entire document" contract; no producer pressure to absorb |
| Two services (L2) | journal Round 7.4 analysis (post-Codex correction): cost > benefit at this scope |
| Aggregate cache / materialised view | brief: "aggregation doesn't need to be fast" |
| ORM declarative models | one table, no relationships, raw SQL is clearer for `PERCENTILE_CONT` / `GREATEST` |
| Alembic migrations | one table, no schema evolution expected; `CREATE TABLE IF NOT EXISTS` is sufficient |
| JSON-structured logging, request IDs, OpenTelemetry | observability is future work |
| Non-root container user, Dockerfile HEALTHCHECK, `tini` | prototype simplicity |

## Real-time dashboards (write-up only)

Flow:

```text
POST /import -> COMMIT -> outbox publisher -> consumer -> Redis pre-aggregated cache -> SSE -> dashboard
```

If real-time dashboards become a product requirement, publish events only after the import transaction commits. A consumer can update Redis pre-aggregated stats per `test_id`, then push changes to dashboards over SSE. That keeps dashboard reads fast without weakening ingest correctness. Postgres remains the source of truth, and `/aggregate` remains the canonical answer when cache state and persisted state disagree.

## Future work

- **Real-time dashboards become a requirement**: introduce an event publisher *after* COMMIT (database remains source of truth), a separate consumer maintaining a Redis hash of pre-aggregated stats per `test_id`, and SSE delivery. `/aggregate` stays as the canonical answer.
- **Many-scanner bursts arrive**: split ingestion and aggregation into separate services. Module/Repository boundary keeps the change local; deploy-level deltas (app factory, lifespan, migration ownership, settings split, test harness) are documented in journal Round 7.1.
- **Batch sizes grow into millions**: switch the write path from multi-VALUES UPSERT to `COPY` into a staging table, then a single set-based MERGE into the main table.
- **Observability matters**: add structured logging, request IDs, OpenTelemetry tracing on parse / validate / upsert phases, Prometheus metrics on rejection rate, batch size distribution, end-to-end latency.
- **Schema evolves**: introduce Alembic migrations.
- **Test-id metadata becomes useful**: separate `tests` table referenced by foreign key.

## Running tests

```bash
uv sync && uv run pytest
```

Tests use testcontainers and require Docker. To run against an existing database:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/markr uv run pytest
```

## Commands appendix

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src/markr
uv run pytest
docker compose down -v
```
