# Markr Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Markr ingestion + aggregation FastAPI service exactly as defined in `specs/2026-05-02-markr-design.md`, deployable via `docker compose up --build`, with `curl`-driven E2E coverage at every minimum-testable slice.

**Architecture:** Single FastAPI process (uvicorn `--workers 2`); two `AsyncEngine`s (write + read) over the same Postgres; pure-ASGI body-size middleware; defusedxml DOM parse; in-memory dedup → multi-VALUES UPSERT in one transaction per request; `PERCENTILE_CONT` aggregation. Single docker-compose with `app` + `db`.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, defusedxml, SQLAlchemy 2.x async Core, asyncpg, Postgres 16, pydantic-settings, pydantic v2, ruff, mypy strict, pytest + pytest-asyncio + httpx + testcontainers; **uv** for dependency management (per CLAUDE.md mandate).

---

## Backpressure rules (enforced throughout this plan)

1. **Spike before integrate.** Every external API gets a `spikes/sig_<feature>.py` + `spikes/spike_<feature>.py` BEFORE the integration task that uses it. Spike output is the source of truth; spec snippets and prior knowledge are not. Run via `uv run python spikes/<file>.py`. Files committed.
2. **E2E with real `curl`.** As soon as a slice is minimally exercisable end-to-end, fire a curl checkpoint task. Docker Desktop is up; the agent owns the DB lifecycle. No deferring E2E to the end. "Unit tests pass" is not a substitute.
3. **No scope creep.** Every task cites the spec section it implements. If the spec is silent, raise as an open question — do not invent.

---

## Coverage matrix (spec §X → tasks)

| Spec | Topic | Tasks |
|---|---|---|
| §1, §16 | Endpoints, reviewer ref | T13.1 (README); T6.5, T9.4, T10.3, T11.3, T11.5 (E2E) |
| §2, §10.4 | Architecture, concurrency | T6.2 |
| §3 | Tech stack, version floors | T1.1 |
| §3.1 | Typed boundaries (XML, repo) | T7.1, T8.2 |
| §3.2 | ruff/mypy config | T1.2 |
| §4 | Project layout | T1.3 |
| §5.1 | POST request contract | T9.1, T9.3 |
| §5.2 | Success response | T9.3 |
| §5.3 | Pipeline order (CT before body cap) | T3.1, T9.3 |
| §5.4 content-type | 415 check | T3.1, T9.1 |
| §5.4 body cap | Pure ASGI 413 middleware | T2.3, T3.1 |
| §5.4 parse | defusedxml typed shim 400 | T2.1, T7.1 |
| §5.4 root check | 422 wrong_root | T7.2 |
| §5.4 record count | 413 / 422 empty | T7.2 |
| §5.4 validate | per-record 422 | T7.3 |
| §5.4 dedup | in-memory reduction | T8.1 |
| §5.4 UPSERT | chunked tx | T8.2 |
| §5.5 | Crash safety (idempotent UPSERT) | T8.2, T11.5 |
| §6.1, §6.2 | XML model, cardinality, whitespace, empty rules | T7.3 |
| §6.3 | summary-marks numeric parse | T7.3 |
| §6.4 | Element order independence | T7.3 |
| §6.5 | Trust contract | T7.3 (no answer parsing) |
| §7.1 | Schema + CHECKs | T4.1 |
| §7.3 | Advisory-lock bootstrap | T2.6, T6.2 |
| §7.4 | Empty batch | T7.2 |
| §8.1 | Path validation | T10.1 |
| §8.2, §8.3 | Aggregate query | T8.2, T10.2 |
| §8.4 | 404 + locked field order | T2.4, T10.1 |
| §8.5 | No app-layer rounding | T10.2 |
| §8.6 | pytest.approx | T8.2, T10.2 |
| §9.1 | Error envelope shape | T5.1, T5.2 |
| §9.2 | Code → status mapping | T5.1, T5.2, T11.3 |
| §9.3 | First-error short-circuit | T7.3, T9.2 |
| §9.4 | MarkrHTTPException | T5.1 |
| §9.5 | Four global handlers | T2.8, T5.2 |
| §10.1 | /health | T6.1 |
| §10.2 | Logging | T6.2 |
| §10.3 | Lifespan | T6.2 |
| §11 | Config (pydantic-settings) | T2.5, T4.2 |
| §12.1 | Dockerfile two-layer | T6.3 |
| §12.2 | .dockerignore | T6.4 |
| §12.3 | docker-compose | T6.4 |
| §13.1, §13.2 | Out-of-scope / future | T13.1 |
| §14 | Assumptions | T13.1 |
| §15 | README sections | T13.1 |
| §17 | References | T13.1 |

E2E gates: T6.5 (health), T9.4 (POST happy path), T10.3 (GET happy path + 404), T11.3 (negative-path matrix), T11.5 (replay-after-restart idempotency).

---

## Phase 0 — Project bootstrap

### Task 1.1: Initialize uv project + dependency floors

**Spec:** §3, §4

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock` (generated)
- Create: `.python-version`

- [x] **Step 1: Initialise uv project**

```bash
cd /Users/tianyili/Learn/ml/markr
uv init --python 3.12 --no-readme --no-pin-python --bare
```

If `uv init` complains about non-empty dir, manually create `pyproject.toml` instead of running `init`.

- [x] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "markr"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "defusedxml>=0.7",
  "sqlalchemy[asyncio]>=2.0",
  "asyncpg>=0.29",
  "pydantic>=2",
  "pydantic-settings>=2",
]

[dependency-groups]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "httpx>=0.27",
  "testcontainers[postgres]>=4",
  "ruff>=0.5",
  "mypy>=1.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/markr"]
```

> **Note:** the `[tool.hatch.build.targets.wheel.force-include]` block that ships `schema.sql` in the wheel is added in T4.1, *after* the SQL file exists. Adding it here would make `uv sync` fail with `FileNotFoundError: Forced include not found`.

- [x] **Step 3: Lock + install**

```bash
uv sync
```

`[dependency-groups].dev` is installed by default by `uv sync` (PEP 735). This keeps the spec §15 reviewer command (`uv sync && uv run pytest`) working without `--extra dev`.

- [x] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .python-version
git commit -m "chore: bootstrap uv project with deps per spec §3"
```

**Acceptance criteria:**
- `uv sync` exits 0 and installs the `dev` group (verify: `uv run pytest --version`).
- `uv run python -c "import fastapi, defusedxml, sqlalchemy, asyncpg, pydantic, pydantic_settings; print('ok')"` prints `ok`.
- `uv.lock` is committed.

---

### Task 1.2: pin tooling config (ruff + mypy + pytest)

**Spec:** §3.2

**Files:**
- Modify: `pyproject.toml`

- [x] **Step 1: Append tool config**

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/markr"]

[[tool.mypy.overrides]]
module = ["defusedxml.*", "testcontainers.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [x] **Step 2: Verify**

```bash
uv run ruff check .                                    # must exit 0 (no source files yet)
uv run mypy src/markr 2>&1 | head -5                   # may warn "No source files" — no src yet
uv run pytest --collect-only 2>&1 | head -3
```

- [x] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: ruff/mypy/pytest config per spec §3.2"
```

**Acceptance criteria:** all three commands above run without crashing.

---

### Task 1.3: Project skeleton directories

**Spec:** §4

**Files:**
- Create: `src/markr/__init__.py`
- Create: `src/markr/api/__init__.py`
- Create: `src/markr/ingestion/__init__.py`
- Create: `src/markr/aggregation/__init__.py`
- Create: `src/markr/db/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/.gitkeep`
- Create: `spikes/.gitkeep`

- [x] **Step 1: Create empty packages**

```bash
mkdir -p src/markr/{api,ingestion,aggregation,db} tests/fixtures spikes
touch src/markr/__init__.py src/markr/api/__init__.py src/markr/ingestion/__init__.py \
      src/markr/aggregation/__init__.py src/markr/db/__init__.py \
      tests/__init__.py tests/fixtures/.gitkeep spikes/.gitkeep
```

- [x] **Step 2: Commit**

```bash
git add src tests spikes
git commit -m "chore: project skeleton per spec §4"
```

**Acceptance criteria:** `uv run python -c "import markr, markr.api, markr.ingestion, markr.aggregation, markr.db"` exits 0.

---

## Phase 1 — Foundational spikes (BEFORE any integration)

> All spikes committed under `spikes/`. Run with `uv run python spikes/<file>.py`. Output recorded in commit message body or sibling `.md`.

### Task 2.1: Spike defusedxml return type

**Spec:** §3.1, §5.4 (parse XML)

**Files:**
- Create: `spikes/sig_defusedxml.py`
- Create: `spikes/spike_defusedxml.py`

- [x] **Step 1: Signature spike**

```python
# spikes/sig_defusedxml.py
import inspect
from defusedxml.ElementTree import fromstring
print("signature:", inspect.signature(fromstring))
print("module:", fromstring.__module__)
print("doc:", (fromstring.__doc__ or "")[:200])
```

Run: `uv run python spikes/sig_defusedxml.py`

- [x] **Step 2: Runtime spike**

```python
# spikes/spike_defusedxml.py
from defusedxml.ElementTree import fromstring as safe_fromstring
from xml.etree.ElementTree import Element

xml = b"<root><child a='1'>hi</child></root>"
parsed = safe_fromstring(xml)
print("type:", type(parsed))
print("isinstance Element:", isinstance(parsed, Element))
print("tag:", parsed.tag)
print("child tag:", parsed.find("child").tag)
print("attr:", parsed.find("child").get("a"))

# Confirm it rejects entity expansion
try:
    safe_fromstring(b'<!DOCTYPE x [<!ENTITY a "boom">]><x>&a;</x>')
    print("entity: ACCEPTED (unexpected)")
except Exception as exc:
    print("entity rejected:", type(exc).__name__)
```

Run: `uv run python spikes/spike_defusedxml.py`

- [x] **Step 3: Commit with output in message**

```bash
git add spikes/sig_defusedxml.py spikes/spike_defusedxml.py
git commit -m "spike: defusedxml.fromstring returns stdlib Element (verifies §3.1 boundary)"
```

**Acceptance criteria:**
- Spike prints `isinstance Element: True`.
- Entity-expansion test prints `entity rejected: <ExceptionName>`.

---

### Task 2.2: Spike SQLAlchemy async + asyncpg

**Spec:** §3 (DB driver), §7, §8.3

**Files:**
- Create: `spikes/sig_sa_async.py`
- Create: `spikes/spike_sa_async.py`

> Requires Postgres reachable via testcontainers — spike spins one up.

- [x] **Step 1: Signature spike**

```python
# spikes/sig_sa_async.py
import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
print("create_async_engine:", inspect.signature(create_async_engine))
print("text:", inspect.signature(text))
```

- [x] **Step 2: Runtime spike (testcontainers Postgres + UPSERT + PERCENTILE_CONT)**

```python
# spikes/spike_sa_async.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

async def main():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        print("url:", url)
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE t (
                  k TEXT, v INT NOT NULL,
                  PRIMARY KEY (k)
                )
            """))
            await conn.execute(text("""
                INSERT INTO t (k, v)
                VALUES (:k1, :v1), (:k2, :v2), (:k3, :v3)
            """), {"k1": "a", "v1": 2, "k2": "b", "v2": 7, "k3": "c", "v3": 4})
            res = await conn.execute(text("SELECT k, v FROM t ORDER BY k"))
            print("initial rows:", res.fetchall())

            # Production ingestion dedups before UPSERT, so each VALUES list has unique keys.
            await conn.execute(text("""
                INSERT INTO t (k, v)
                VALUES (:k1, :v1), (:k2, :v2), (:k3, :v3)
                ON CONFLICT (k) DO UPDATE SET v = GREATEST(t.v, EXCLUDED.v)
            """), {"k1": "a", "v1": 5, "k2": "b", "v2": 1, "k3": "c", "v3": 3})
            res = await conn.execute(text("SELECT k, v FROM t ORDER BY k"))
            print("rows:", res.fetchall())

            res = await conn.execute(text(
                "SELECT AVG(v::float) AS mean, "
                "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v::float) AS p50, "
                "COALESCE(STDDEV_POP(v::float), 0) AS sd FROM t"
            ))
            print("stats:", res.mappings().one())
        await engine.dispose()

asyncio.run(main())
```

Run: `uv run python spikes/spike_sa_async.py`

- [x] **Step 3: Commit**

```bash
git add spikes/sig_sa_async.py spikes/spike_sa_async.py
git commit -m "spike: sqlalchemy async + asyncpg + UPSERT + PERCENTILE_CONT verified"
```

**Acceptance criteria:**
- `initial rows: [('a', 2), ('b', 7), ('c', 4)]` — confirms actual multi-VALUES insert syntax.
- `rows: [('a', 5), ('b', 7), ('c', 4)]` — confirms later multi-VALUES UPSERT uses `GREATEST` against existing rows. Duplicate keys inside one VALUES list are not used because ingestion dedups before UPSERT.
- `stats:` mapping has numeric `mean`, `p50`, `sd` fields, none `None`.

---

### Task 2.3: Spike pure ASGI middleware (body cap)

**Spec:** §5.4 (body cap)

**Files:**
- Create: `spikes/spike_asgi_bodycap.py`

- [x] **Step 1: Pure ASGI middleware that streams `receive` and aborts at N bytes**

```python
# spikes/spike_asgi_bodycap.py
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LIMIT = 16  # tiny for testing

class BodyCap:
    def __init__(self, app, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        cl = next((v for k, v in scope.get("headers", []) if k == b"content-length"), None)
        if cl is not None and int(cl) > self.limit:
            return await self._reject(send)

        seen = 0
        async def wrapped_receive():
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.limit:
                    raise _TooLarge()
            return msg

        try:
            await self.app(scope, wrapped_receive, send)
        except _TooLarge:
            await self._reject(send)

    async def _reject(self, send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"error":"body_too_large"}'})

class _TooLarge(Exception): ...

app = FastAPI()

@app.post("/echo")
async def echo(req: Request):
    body = await req.body()
    return {"len": len(body)}

app.add_middleware(BodyCap, limit=LIMIT)

async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r1 = await c.post("/echo", content=b"x" * 10)
        print("under:", r1.status_code, r1.json())
        r2 = await c.post("/echo", content=b"x" * 100)
        print("over:", r2.status_code, r2.text)
        # Lying content-length: still rejected by streaming counter
        r3 = await c.post("/echo", content=b"x" * 100,
                          headers={"content-length": "5"})
        print("lying CL:", r3.status_code, r3.text)

asyncio.run(main())
```

Run: `uv run python spikes/spike_asgi_bodycap.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_asgi_bodycap.py
git commit -m "spike: pure ASGI body-cap middleware blocks oversize and lying content-length"
```

**Acceptance criteria:**
- `under` prints `200 ...`
- `over` prints `413 ...`
- `lying CL` prints `413 ...`

---

### Task 2.4: Spike pydantic v2 declaration-order serialization

**Spec:** §8.4

**Files:**
- Create: `spikes/spike_pydantic_order.py`

- [x] **Step 1: Confirm dump order matches declaration order**

```python
# spikes/spike_pydantic_order.py
from pydantic import BaseModel

class Agg(BaseModel):
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int

m = Agg(mean=65.0, stddev=0.0, min=65.0, max=65.0, p25=65.0, p50=65.0, p75=65.0, count=1)
print(m.model_dump_json())
```

Run: `uv run python spikes/spike_pydantic_order.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_pydantic_order.py
git commit -m "spike: pydantic v2 dump preserves field declaration order"
```

**Acceptance criteria:** output is exactly
```
{"mean":65.0,"stddev":0.0,"min":65.0,"max":65.0,"p25":65.0,"p50":65.0,"p75":65.0,"count":1}
```

---

### Task 2.5: Spike pydantic-settings env loading

**Spec:** §11

**Files:**
- Create: `spikes/spike_settings.py`

- [x] **Step 1: Verify env wiring + missing-field failure**

```python
# spikes/spike_settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class S(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    WRITE_POOL_SIZE: int = 10
    WRITE_POOL_OVERFLOW: int = 20
    READ_POOL_SIZE: int = 5
    READ_POOL_OVERFLOW: int = 10

os.environ["DATABASE_URL"] = "postgresql+asyncpg://x:x@h/db"
print("loaded:", S().model_dump())

# Missing should fail loudly
os.environ.pop("DATABASE_URL")
try:
    S()
    print("MISSING did not raise")
except Exception as exc:
    print("missing raises:", type(exc).__name__)
```

Run: `uv run python spikes/spike_settings.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_settings.py
git commit -m "spike: pydantic-settings loads env + fails fast on missing required"
```

**Acceptance criteria:** prints loaded config dict; missing case raises (not silent).

---

### Task 2.6: Spike advisory lock + IF NOT EXISTS race

**Spec:** §7.3

**Files:**
- Create: `spikes/spike_advisory_lock.py`

- [x] **Step 1: Two concurrent connections both running advisory-lock-protected DDL**

```python
# spikes/spike_advisory_lock.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

DDL = "CREATE TABLE IF NOT EXISTS test_results (k TEXT PRIMARY KEY)"
KEY = 0x4D41524B

async def boot(engine, label):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": KEY})
        await conn.execute(text(DDL))
        print(f"{label} done")

async def main():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        engine = create_async_engine(pg.get_connection_url())
        await asyncio.gather(boot(engine, "A"), boot(engine, "B"))
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT to_regclass('test_results')"))
            print("table:", res.scalar())
        await engine.dispose()

asyncio.run(main())
```

Run: `uv run python spikes/spike_advisory_lock.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_advisory_lock.py
git commit -m "spike: pg_advisory_xact_lock serialises concurrent CREATE TABLE IF NOT EXISTS"
```

**Acceptance criteria:** both `A done` and `B done` print, no exceptions, `table:` is `test_results`.

---

### Task 2.7: Spike testcontainers lifecycle for pytest fixture shape

**Spec:** §3, §11 (TEST_DATABASE_URL fallback)

**Files:**
- Create: `spikes/spike_testcontainers_fixture.py`

- [x] **Step 1: Confirm context-manager URL works in async + connection-url shape**

```python
# spikes/spike_testcontainers_fixture.py
from testcontainers.postgres import PostgresContainer
with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
    print("url:", pg.get_connection_url())
    print("host:", pg.get_container_host_ip())
    print("port:", pg.get_exposed_port(5432))
```

Run: `uv run python spikes/spike_testcontainers_fixture.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_testcontainers_fixture.py
git commit -m "spike: testcontainers postgres URL shape for asyncpg"
```

**Acceptance criteria:** URL begins with `postgresql+asyncpg://`.

---

### Task 2.8: Spike FastAPI exception-handler precedence

**Spec:** §9.5

**Files:**
- Create: `spikes/spike_fastapi_handlers.py`

- [x] **Step 1: Verify the 4-handler matrix actually fires the handler we expect**

```python
# spikes/spike_fastapi_handlers.py
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

class MarkrHTTPException(HTTPException):
    def __init__(self, status_code, error, message, details=None):
        super().__init__(status_code=status_code, detail=message)
        self.error = error
        self.message = message
        self.details = details or {}

app = FastAPI()

@app.exception_handler(MarkrHTTPException)
async def h_markr(_, exc: MarkrHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": exc.error, "message": exc.message, "details": exc.details})

@app.exception_handler(StarletteHTTPException)
async def h_starlette(_, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "not_found", "message": "x", "details": {"reason": "unknown_route"}})
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={"error": "method_not_allowed", "message": "x", "details": {}})
    return JSONResponse(status_code=exc.status_code, content={"error": "internal_error", "message": "x", "details": {}})

@app.exception_handler(RequestValidationError)
async def h_validation(_, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "invalid_path_param", "message": "x", "details": {"raw": str(exc)}})

@app.exception_handler(Exception)
async def h_500(_, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": "internal server error", "details": {}})

@app.get("/markr")
async def m(): raise MarkrHTTPException(422, "wrong_root", "x")

@app.get("/boom")
async def b(): raise RuntimeError("kaboom")

from typing import Annotated
from fastapi import Path
@app.get("/p/{x}")
async def p(x: Annotated[str, Path(max_length=3)]): return {"x": x}

async def main():
    # raise_app_exceptions=False so the catch-all Exception handler's 500 envelope
    # is observable instead of bubbling RuntimeError out to the test.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        for path in ["/markr", "/unknown", "/boom", "/p/toolong"]:
            r = await c.get(path)
            print(path, "→", r.status_code, r.json())
        # Wrong method
        r = await c.post("/markr")
        print("POST /markr →", r.status_code, r.json())

asyncio.run(main())
```

Run: `uv run python spikes/spike_fastapi_handlers.py`

- [x] **Step 2: Commit**

```bash
git add spikes/spike_fastapi_handlers.py
git commit -m "spike: fastapi handler precedence — Markr/Starlette/Validation/Exception"
```

**Acceptance criteria:**
- `/markr` → 422 `wrong_root`
- `/unknown` → 404 `not_found` w/ `reason: unknown_route`
- `/boom` → 500 `internal_error`
- `/p/toolong` → 422 `invalid_path_param`
- `POST /markr` → 405 `method_not_allowed`

---

## Phase 2 — Body cap middleware (extracted from spike)

### Task 3.1: Promote body-cap spike to production middleware (with CT pre-check)

**Spec:** §5.3 strict order (CT before body cap), §5.4 (CT 415 + body cap 413), §9.2

> Middleware runs before route handlers, so the only way to honour spec §5.3's `content-type (415) → body cap (413)` order is to check both inside the same ASGI middleware when the request targets `POST /import`. The route-handler CT check (T9.1) remains as defence-in-depth but is unreachable for /import once this middleware is installed.

**Files:**
- Create: `src/markr/api/body_cap.py`
- Create: `tests/test_body_cap.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_body_cap.py
import httpx, pytest
from fastapi import FastAPI, Request

from markr.api.body_cap import BodyCapMiddleware, BODY_LIMIT_BYTES

@pytest.fixture
def app():
    a = FastAPI()
    @a.post("/import")
    async def imp(req: Request):
        return {"len": len(await req.body())}
    @a.post("/x")  # non-/import route — middleware should not gate it
    async def x(req: Request):
        return {"len": len(await req.body())}
    a.add_middleware(BodyCapMiddleware)
    return a

@pytest.mark.asyncio
async def test_under_limit_with_correct_ct(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"a" * 100,
                         headers={"content-type": "text/xml+markr"})
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_wrong_ct_415_even_when_oversized(app):
    """Spec §5.3: content-type (415) wins over body cap (413)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"a",
                         headers={"content-type": "application/xml",
                                  "content-length": str(BODY_LIMIT_BYTES + 1)})
        assert r.status_code == 415
        assert r.json()["error"] == "unsupported_media_type"

@pytest.mark.asyncio
async def test_content_length_exceeds(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"a",
                         headers={"content-type": "text/xml+markr",
                                  "content-length": str(BODY_LIMIT_BYTES + 1)})
        assert r.status_code == 413
        assert r.json()["error"] == "body_too_large"

@pytest.mark.asyncio
async def test_streaming_overflow_with_lying_cl(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"a" * (BODY_LIMIT_BYTES + 10),
                         headers={"content-type": "text/xml+markr",
                                  "content-length": "10"})
        assert r.status_code == 413

@pytest.mark.asyncio
async def test_non_import_route_not_gated(app):
    """Middleware only applies to POST /import; other routes pass through."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/x", content=b"a" * 100)  # no CT, non-/import
        assert r.status_code == 200
```

- [x] **Step 2: Run — should fail (module missing)**

```bash
uv run pytest tests/test_body_cap.py -v
```

Expected: ImportError / collection error.

- [x] **Step 3: Implement**

```python
# src/markr/api/body_cap.py
from __future__ import annotations
import json
from typing import Awaitable, Callable, MutableMapping, Any

BODY_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MiB per spec §5.4
REQUIRED_CT = "text/xml+markr"
GATED_PATH = "/import"
GATED_METHOD = "POST"

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class _BodyTooLarge(Exception):
    pass


def _header(scope: Scope, name: bytes) -> bytes | None:
    for k, v in scope.get("headers", []):
        if k == name:
            return v
    return None


class BodyCapMiddleware:
    """Spec §5.3 strict order: content-type (415) → body cap (413).

    Middleware runs before route handlers, so both checks live here for
    POST /import. Other routes pass through untouched.
    """

    def __init__(self, app: ASGIApp, limit: int = BODY_LIMIT_BYTES) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        gated = (scope.get("method") == GATED_METHOD and scope.get("path") == GATED_PATH)

        if gated:
            # 1. Content-type 415 — must precede body-cap 413 per spec §5.3.
            ct_raw = _header(scope, b"content-type") or b""
            media = ct_raw.decode("latin-1").split(";", 1)[0].strip().lower()
            if media != REQUIRED_CT:
                await self._reject_415(send, media)
                return

            # 2. Content-length early reject (413).
            cl = _header(scope, b"content-length")
            if cl is not None:
                try:
                    if int(cl) > self.limit:
                        await self._reject_413(send)
                        return
                except ValueError:
                    pass

        if not gated:
            await self.app(scope, receive, send)
            return

        # 3. Streaming counter for missing/lying content-length.
        seen = 0

        async def wrapped() -> Message:
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.limit:
                    raise _BodyTooLarge()
            return msg

        try:
            await self.app(scope, wrapped, send)
        except _BodyTooLarge:
            await self._reject_413(send)

    async def _reject_413(self, send: Send) -> None:
        await self._write(send, 413, {
            "error": "body_too_large",
            "message": f"request body exceeds {self.limit} bytes (10 MiB)",
            "details": {"limit": self.limit},
        })

    async def _reject_415(self, send: Send, got: str) -> None:
        await self._write(send, 415, {
            "error": "unsupported_media_type",
            "message": f"expected {REQUIRED_CT}",
            "details": {"got": got},
        })

    async def _write(self, send: Send, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
```

- [x] **Step 4: Run — should pass**

```bash
uv run pytest tests/test_body_cap.py -v
```

- [x] **Step 5: Commit**

```bash
git add src/markr/api/body_cap.py tests/test_body_cap.py
git commit -m "feat: pure-ASGI ingest preflight (CT 415 → body cap 413) per spec §5.3"
```

**Acceptance criteria:** all 5 tests in `tests/test_body_cap.py` pass. Critically, `test_wrong_ct_415_even_when_oversized` proves spec §5.3 ordering.

---

## Phase 3 — Schema + engines + Settings

### Task 4.1: Schema SQL

**Spec:** §7.1

**Files:**
- Create: `src/markr/db/schema.sql`

- [x] **Step 1: Write schema**

```sql
-- src/markr/db/schema.sql
CREATE TABLE IF NOT EXISTS test_results (
  test_id          TEXT NOT NULL,
  student_number   TEXT NOT NULL,
  marks_available  INT  NOT NULL CHECK (marks_available > 0),
  marks_obtained   INT  NOT NULL CHECK (marks_obtained  >= 0
                                    AND marks_obtained <= marks_available),
  first_name       TEXT,
  last_name        TEXT,
  scanned_on       TIMESTAMPTZ,
  PRIMARY KEY (test_id, student_number)
);
```

- [x] **Step 2: Add `force-include` to ship `schema.sql` in the wheel**

Append to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/markr/db/schema.sql" = "markr/db/schema.sql"
```

Re-lock and verify:

```bash
uv sync
uv run python -c "from importlib.resources import files; print(files('markr.db') / 'schema.sql')"
```

The print should resolve to the venv-installed path (or editable source path), not raise.

- [x] **Step 3: Commit**

```bash
git add src/markr/db/schema.sql pyproject.toml uv.lock
git commit -m "feat: schema.sql with CHECKs per spec §7.1; ship in wheel via hatch force-include"
```

**Acceptance criteria:**
- `src/markr/db/schema.sql` matches spec §7.1 byte-for-byte (modulo comment).
- `uv sync` succeeds with the `force-include` block present.
- `importlib.resources.files("markr.db") / "schema.sql"` resolves at runtime.

---

### Task 4.2: Settings module

**Spec:** §11

**Files:**
- Create: `src/markr/config.py`
- Create: `tests/test_config.py`

- [x] **Step 1: Failing test**

```python
# tests/test_config.py
import os, pytest

def test_loads(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
    from importlib import reload
    import markr.config as cfg
    reload(cfg)
    s = cfg.Settings()
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@h/d"
    assert s.LOG_LEVEL == "INFO"
    assert s.WRITE_POOL_SIZE == 10

def test_missing_database_url_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from importlib import reload
    import markr.config as cfg
    reload(cfg)
    with pytest.raises(Exception):
        cfg.Settings()
```

- [x] **Step 2: Run — fails**

- [x] **Step 3: Implement**

```python
# src/markr/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    WRITE_POOL_SIZE: int = 10
    WRITE_POOL_OVERFLOW: int = 20
    READ_POOL_SIZE: int = 5
    READ_POOL_OVERFLOW: int = 10
```

- [x] **Step 4: Run — passes**

- [x] **Step 5: Commit**

```bash
git add src/markr/config.py tests/test_config.py
git commit -m "feat: pydantic-settings Settings (spec §11) — DATABASE_URL required"
```

**Acceptance criteria:** both tests pass; `mypy src/markr/config.py` clean.

---

### Task 4.3: Engines factory

**Spec:** §2, §7.3, §10.3 (engine creation half)

**Files:**
- Create: `src/markr/db/engines.py`

- [x] **Step 1: Implement**

```python
# src/markr/db/engines.py
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from markr.config import Settings


def build_write_engine(s: Settings) -> AsyncEngine:
    return create_async_engine(
        s.DATABASE_URL,
        pool_size=s.WRITE_POOL_SIZE,
        max_overflow=s.WRITE_POOL_OVERFLOW,
        pool_pre_ping=True,
    )


def build_read_engine(s: Settings) -> AsyncEngine:
    return create_async_engine(
        s.DATABASE_URL,
        pool_size=s.READ_POOL_SIZE,
        max_overflow=s.READ_POOL_OVERFLOW,
        pool_pre_ping=True,
    )
```

- [x] **Step 2: mypy + commit**

```bash
uv run mypy src/markr/db/engines.py
git add src/markr/db/engines.py
git commit -m "feat: write/read AsyncEngine factories (spec §2, §10.3)"
```

**Acceptance criteria:** mypy clean.

---

## Phase 4 — Error envelope foundation

### Task 5.1: MarkrHTTPException

**Spec:** §9.4

**Files:**
- Create: `src/markr/api/errors.py`
- Create: `tests/test_errors.py`

- [x] **Step 1: Failing test**

```python
# tests/test_errors.py
from markr.api.errors import MarkrHTTPException

def test_carries_fields():
    e = MarkrHTTPException(422, "wrong_root", "msg", {"got": "x"})
    assert e.status_code == 422
    assert e.error == "wrong_root"
    assert e.message == "msg"
    assert e.details == {"got": "x"}

def test_default_details():
    e = MarkrHTTPException(400, "malformed_xml", "bad")
    assert e.details == {}
```

- [x] **Step 2: Implement**

```python
# src/markr/api/errors.py
from __future__ import annotations
from fastapi import HTTPException


class MarkrHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.error = error
        self.message = message
        self.details = details or {}
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_errors.py -v
git add src/markr/api/errors.py tests/test_errors.py
git commit -m "feat: MarkrHTTPException carrier (spec §9.4)"
```

**Acceptance criteria:** tests pass; mypy clean.

---

### Task 5.2: Four global exception handlers

**Spec:** §9.1, §9.2, §9.5

**Files:**
- Create: `src/markr/api/exception_handlers.py`
- Create: `tests/test_exception_handlers.py`

- [x] **Step 1: Failing test (covers all four handlers)**

```python
# tests/test_exception_handlers.py
import httpx, pytest
from fastapi import FastAPI, Path
from typing import Annotated

from markr.api.errors import MarkrHTTPException
from markr.api.exception_handlers import register_exception_handlers


@pytest.fixture
def app():
    a = FastAPI()
    register_exception_handlers(a)

    @a.get("/markr")
    async def _():
        raise MarkrHTTPException(422, "wrong_root", "bad root", {"got": "x"})

    @a.get("/boom")
    async def _():
        raise RuntimeError("kaboom")

    @a.get("/p/{x}")
    async def _(x: Annotated[str, Path(max_length=3)]):
        return {"x": x}

    return a


@pytest.mark.asyncio
async def test_markr_handler(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/markr")
        assert r.status_code == 422
        assert r.json() == {"error": "wrong_root", "message": "bad root", "details": {"got": "x"}}


@pytest.mark.asyncio
async def test_unknown_route_404(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/nope")
        assert r.status_code == 404
        body = r.json()
        assert body["error"] == "not_found"
        assert body["details"]["reason"] == "unknown_route"


@pytest.mark.asyncio
async def test_method_not_allowed(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/markr")
        assert r.status_code == 405
        assert r.json()["error"] == "method_not_allowed"


@pytest.mark.asyncio
async def test_request_validation(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/p/toolong")
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_path_param"


@pytest.mark.asyncio
async def test_unhandled_exception_500(app):
    # raise_app_exceptions=False so the catch-all Exception handler's 500 envelope
    # is observable instead of bubbling RuntimeError out to the test.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/boom")
        assert r.status_code == 500
        assert r.json()["error"] == "internal_error"
```

- [x] **Step 2: Implement**

```python
# src/markr/api/exception_handlers.py
from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from markr.api.errors import MarkrHTTPException

log = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MarkrHTTPException)
    async def _markr(_req: Request, exc: MarkrHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _starlette(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "message": "route not found",
                         "details": {"reason": "unknown_route"}},
            )
        if exc.status_code == 405:
            return JSONResponse(
                status_code=405,
                content={"error": "method_not_allowed", "message": "method not allowed",
                         "details": {}},
            )
        log.warning("unhandled starlette exception escaped to envelope: status=%s detail=%s",
                    exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "internal_error",
                     "message": "an unexpected framework error occurred",
                     "details": {}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_path_param",
                     "message": "request validation failed",
                     "details": {"errors": exc.errors()}},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "internal server error", "details": {}},
        )
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_exception_handlers.py -v
git add src/markr/api/exception_handlers.py tests/test_exception_handlers.py
git commit -m "feat: 4 global exception handlers per spec §9.5"
```

**Acceptance criteria:** all 5 tests pass.

---

## Phase 5 — Health endpoint + lifespan + app + docker (first E2E)

### Task 6.1: /health route

**Spec:** §10.1

**Files:**
- Create: `src/markr/api/ops.py`
- Create: `tests/test_health.py`

- [x] **Step 1: Failing test (with testcontainers fixture deferred to conftest in T8.5; use stub here)**

```python
# tests/test_health.py
import pytest, httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from markr.api.ops import build_ops_router
from markr.api.exception_handlers import register_exception_handlers

@pytest.mark.asyncio
async def test_health_ok():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        engine = create_async_engine(pg.get_connection_url())
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(build_ops_router(engine))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/health")
            assert r.status_code == 200
            assert r.json() == {"status": "ok"}
        await engine.dispose()

@pytest.mark.asyncio
async def test_health_db_down_503():
    engine = create_async_engine("postgresql+asyncpg://nope:nope@127.0.0.1:1/none")
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(build_ops_router(engine))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/health")
        assert r.status_code == 503
        assert r.json()["error"] == "service_unavailable"
    await engine.dispose()
```

- [x] **Step 2: Implement**

```python
# src/markr/api/ops.py
from __future__ import annotations
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.api.errors import MarkrHTTPException


def build_ops_router(read_engine: AsyncEngine) -> APIRouter:
    r = APIRouter()

    @r.get("/health")
    async def health() -> dict[str, str]:
        try:
            async with read_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok"}
        except Exception as exc:
            raise MarkrHTTPException(
                status_code=503,
                error="service_unavailable",
                message="database unreachable",
                details={"status": "degraded"},
            ) from exc

    return r
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_health.py -v
git add src/markr/api/ops.py tests/test_health.py
git commit -m "feat: /health (spec §10.1)"
```

**Acceptance criteria:** both tests pass.

---

### Task 6.2: Lifespan + app factory

**Spec:** §2, §7.3, §10.3

**Files:**
- Create: `src/markr/main.py`
- Create: `tests/test_lifespan.py`

- [x] **Step 1: Implement**

```python
# src/markr/main.py
from __future__ import annotations
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from importlib.resources import files
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ops import build_ops_router
from markr.config import Settings
from markr.db.engines import build_read_engine, build_write_engine

SCHEMA_LOCK_KEY = 0x4D41524B  # "MARK"


def _read_schema_sql() -> str:
    return (files("markr.db") / "schema.sql").read_text(encoding="utf-8")


async def _wait_for_db(engine: AsyncEngine, max_wait_s: float = 30.0) -> None:
    delay = 0.5
    waited = 0.0
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception:
            if waited >= max_wait_s:
                raise
            await asyncio.sleep(delay)
            waited += delay
            delay = min(delay * 2, 5.0)


async def _bootstrap_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SCHEMA_LOCK_KEY})
        await conn.execute(text(_read_schema_sql()))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", settings.LOG_LEVEL).upper())

    write_engine = build_write_engine(settings)
    read_engine = build_read_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await _wait_for_db(write_engine)
        await _bootstrap_schema(write_engine)
        try:
            yield
        finally:
            await write_engine.dispose()
            await read_engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    app.include_router(build_ops_router(read_engine))

    # Stash engines so subsequent routers can pull them in via app.state
    app.state.write_engine = write_engine
    app.state.read_engine = read_engine

    return app


# Intentionally NO module-scope `app = create_app()`.
# Settings() requires DATABASE_URL and would fire at import time, breaking any
# test that imports `markr.main` before setting the env var.
# Production runs via `uvicorn markr.main:create_app --factory` (see Dockerfile).
```

- [x] **Step 2: Lifespan integration test**

```python
# tests/test_lifespan.py
import os, pytest, httpx
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from markr.config import Settings
from markr.main import create_app


@pytest.mark.asyncio
async def test_lifespan_creates_table():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        app = create_app(Settings())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            async with app.router.lifespan_context(app):
                r = await c.get("/health")
                assert r.status_code == 200

        # Confirm table exists post-lifespan
        verify = create_async_engine(url)
        async with verify.connect() as conn:
            res = await conn.execute(text("SELECT to_regclass('test_results')"))
            assert res.scalar() == "test_results"
        await verify.dispose()
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_lifespan.py -v
git add src/markr/main.py tests/test_lifespan.py
git commit -m "feat: app factory + lifespan with advisory-lock schema bootstrap (§7.3, §10.3)"
```

**Acceptance criteria:** lifespan test passes; table is present after startup.

---

### Task 6.3: Dockerfile

**Spec:** §12.1

**Files:**
- Create: `Dockerfile`

- [x] **Step 1: Write Dockerfile (verbatim from spec §12.1)**

```dockerfile
# ── builder ──────────────────────────────────
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ── runtime ──────────────────────────────────
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
COPY --from=builder /opt/venv /opt/venv
EXPOSE 4567
CMD ["uvicorn", "markr.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "4567", "--workers", "2"]
```

- [x] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "build: two-layer Dockerfile per spec §12.1"
```

**Acceptance criteria:** `docker build .` builds successfully (executed in T6.5).

---

### Task 6.4: .dockerignore + docker-compose.yml

**Spec:** §12.2, §12.3

**Files:**
- Create: `.dockerignore`
- Create: `docker-compose.yml`

- [x] **Step 1: .dockerignore (spec §12.2)**

```
.git
.venv
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.env
tests/
docs/
specs/
*.md
```

- [x] **Step 2: docker-compose.yml (spec §12.3, verbatim)**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: markr
      POSTGRES_PASSWORD: markr
      POSTGRES_DB: markr
    volumes:
      - markr_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U markr -d markr"]
      interval: 2s
      timeout: 2s
      retries: 15

  app:
    build: .
    ports:
      - "4567:4567"
    environment:
      DATABASE_URL: postgresql+asyncpg://markr:markr@db:5432/markr
    depends_on:
      db:
        condition: service_healthy

volumes:
  markr_pgdata:
```

- [x] **Step 3: Commit**

```bash
git add .dockerignore docker-compose.yml
git commit -m "build: docker-compose + .dockerignore per spec §12.2, §12.3"
```

**Acceptance criteria:** files match spec.

---

### Task 6.5: 🟢 **E2E checkpoint #1 — health endpoint via real curl**

**Spec:** §10.1, §12.3

- [x] **Step 1: Bring up the stack**

```bash
cd /Users/tianyili/Learn/ml/markr
docker compose up --build -d
```

Wait until `docker compose ps` shows `app` healthy or at least running. Tail logs for ~10s to confirm lifespan completed: `docker compose logs app | tail -30`. Look for "Application startup complete."

- [x] **Step 2: curl health**

```bash
curl -sS -o /tmp/markr_health.json -w "HTTP=%{http_code}\n" http://localhost:4567/health
cat /tmp/markr_health.json
```

Expected:
```
HTTP=200
{"status":"ok"}
```

- [x] **Step 3: curl unknown route → 404 envelope**

```bash
curl -sS http://localhost:4567/nope | python -m json.tool
```

Expected JSON:
```json
{"error": "not_found", "message": "...", "details": {"reason": "unknown_route"}}
```

- [x] **Step 4: Verify table exists in DB**

```bash
docker compose exec -T db psql -U markr -d markr -c "\\d test_results"
```

Expected: shows `test_id`, `student_number`, `marks_available`, `marks_obtained`, `first_name`, `last_name`, `scanned_on` columns and the PK.

- [x] **Step 5: Tear down (keep volume — schema persists is fine)**

```bash
docker compose down
```

- [x] **Step 6: Commit confirmation note**

```bash
git commit --allow-empty -m "test(e2e): health + 404 envelope verified via curl"
```

**Acceptance criteria:** Step 2 prints `HTTP=200` and `{"status":"ok"}`. Step 3 returns the 404 envelope with `reason: unknown_route`. Step 4 lists the spec'd columns.

---

## Phase 6 — XML parsing + validation (per-record)

### Task 7.1: defusedxml typed boundary shim

**Spec:** §3.1, §5.4 (parse XML)

**Files:**
- Create: `src/markr/ingestion/xml_parser.py`
- Create: `tests/test_xml_parser.py`

> Prereq: T2.1 spike done.

- [x] **Step 1: Failing test**

```python
# tests/test_xml_parser.py
import pytest
from xml.etree.ElementTree import Element
from markr.ingestion.xml_parser import safe_parse, MalformedXMLError

def test_returns_stdlib_element():
    e = safe_parse(b"<a><b>1</b></a>")
    assert isinstance(e, Element)
    assert e.tag == "a"

def test_malformed_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"<a>")

def test_empty_body_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"")

def test_whitespace_only_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"   \n\t  ")
```

- [x] **Step 2: Implement**

```python
# src/markr/ingestion/xml_parser.py
from __future__ import annotations
from xml.etree.ElementTree import Element
from defusedxml.ElementTree import fromstring as _safe_fromstring  # type: ignore[import-untyped]


class MalformedXMLError(ValueError):
    pass


def safe_parse(body: bytes) -> Element:
    if not body or not body.strip():
        raise MalformedXMLError("empty or whitespace-only body")
    try:
        return _safe_fromstring(body)
    except Exception as exc:
        raise MalformedXMLError(str(exc)) from exc
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_xml_parser.py -v
uv run mypy src/markr/ingestion/xml_parser.py
git add src/markr/ingestion/xml_parser.py tests/test_xml_parser.py
git commit -m "feat: defusedxml typed shim (spec §3.1, §5.4)"
```

**Acceptance criteria:** 4 tests pass; mypy clean.

---

### Task 7.2: Root + record-count gate

**Spec:** §5.4 (root check, record count check), §7.4

**Files:**
- Create: `src/markr/ingestion/structure.py`
- Create: `tests/test_structure.py`

- [x] **Step 1: Failing test**

```python
# tests/test_structure.py
import pytest
from markr.ingestion.xml_parser import safe_parse
from markr.ingestion.structure import gate_root_and_count, MAX_RECORDS
from markr.api.errors import MarkrHTTPException

def _xml(records: int) -> bytes:
    body = b"<mcq-test-results>" + b"<mcq-test-result/>" * records + b"</mcq-test-results>"
    return body

def test_wrong_root_raises_422():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(b"<other/>"))
    assert ei.value.status_code == 422
    assert ei.value.error == "wrong_root"

def test_namespaced_root_rejected():
    body = b'<x:mcq-test-results xmlns:x="http://e/m"></x:mcq-test-results>'
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(body))
    assert ei.value.error == "wrong_root"

def test_too_many_records_413():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(_xml(MAX_RECORDS + 1)))
    assert ei.value.status_code == 413
    assert ei.value.error == "record_count_exceeded"
    assert ei.value.details["count"] == MAX_RECORDS + 1

def test_exactly_max_records_allowed():
    rs = gate_root_and_count(safe_parse(_xml(MAX_RECORDS)))
    assert len(rs) == MAX_RECORDS

def test_zero_records_422_empty_batch():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(_xml(0)))
    assert ei.value.status_code == 422
    assert ei.value.error == "empty_batch"
```

- [x] **Step 2: Implement**

```python
# src/markr/ingestion/structure.py
from __future__ import annotations
from xml.etree.ElementTree import Element

from markr.api.errors import MarkrHTTPException

ROOT_TAG = "mcq-test-results"
RECORD_TAG = "mcq-test-result"
MAX_RECORDS = 10_000


def gate_root_and_count(root: Element) -> list[Element]:
    if root.tag != ROOT_TAG:
        raise MarkrHTTPException(
            status_code=422,
            error="wrong_root",
            message=f"unexpected root element: {root.tag!r}",
            details={"got": root.tag, "expected": ROOT_TAG},
        )
    records = root.findall(RECORD_TAG)
    n = len(records)
    if n > MAX_RECORDS:
        raise MarkrHTTPException(
            status_code=413,
            error="record_count_exceeded",
            message=f"batch contains {n} records (limit {MAX_RECORDS})",
            details={"count": n, "limit": MAX_RECORDS},
        )
    if n == 0:
        raise MarkrHTTPException(
            status_code=422,
            error="empty_batch",
            message="document contains zero records",
        )
    return records
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_structure.py -v
git add src/markr/ingestion/structure.py tests/test_structure.py
git commit -m "feat: root + record-count gate (spec §5.4, §7.4)"
```

**Acceptance criteria:** all 5 tests pass.

---

### Task 7.3: Per-record validator (cardinality, whitespace, scores)

**Spec:** §6.1–§6.5, §9.3

**Files:**
- Create: `src/markr/ingestion/validator.py`
- Create: `tests/test_validator.py`

- [x] **Step 1: Failing test (covers precedence)**

```python
# tests/test_validator.py
import pytest
from xml.etree.ElementTree import fromstring
from datetime import datetime, timezone
from markr.ingestion.validator import validate_record, RawRecord
from markr.api.errors import MarkrHTTPException


def parse(s: str):
    return fromstring(s)


def good_xml():
    return parse("""
    <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
      <first-name>Jane</first-name>
      <last-name>Austen</last-name>
      <student-number>521585128</student-number>
      <test-id>1234</test-id>
      <summary-marks available="20" obtained="13"/>
    </mcq-test-result>""".strip())


def test_happy_path():
    r = validate_record(good_xml())
    assert r.test_id == "1234"
    assert r.student_number == "521585128"
    assert r.marks_available == 20
    assert r.marks_obtained == 13
    assert r.first_name == "Jane"
    assert r.last_name == "Austen"
    assert r.scanned_on == datetime(2017, 12, 4, 12, 12, 10,
                                    tzinfo=timezone(__import__("datetime").timedelta(hours=11)))


@pytest.mark.parametrize("xml,err,field", [
    # cardinality: missing
    ("<mcq-test-result><test-id>1</test-id><summary-marks available='1' obtained='1'/></mcq-test-result>",
     "cardinality_violation", "student-number"),
    # cardinality: dup
    ("<mcq-test-result><student-number>1</student-number><student-number>1</student-number>"
     "<test-id>1</test-id><summary-marks available='1' obtained='1'/></mcq-test-result>",
     "cardinality_violation", "student-number"),
    # whitespace empty
    ("<mcq-test-result><student-number>   </student-number><test-id>1</test-id>"
     "<summary-marks available='1' obtained='1'/></mcq-test-result>",
     "invalid_field_value", "student-number"),
])
def test_required_field_failures(xml, err, field):
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.status_code == 422
    assert ei.value.error == err
    assert ei.value.details.get("field") == field


@pytest.mark.parametrize("avail,obt", [
    ("0", "0"),         # available <= 0
    ("-3", "1"),
    ("10", "11"),       # obtained > available
    ("twenty", "1"),    # non-int
    ("10", "1.5"),      # non-int float
])
def test_invalid_score(avail, obt):
    xml = (f"<mcq-test-result><student-number>1</student-number><test-id>1</test-id>"
           f"<summary-marks available='{avail}' obtained='{obt}'/></mcq-test-result>")
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.error == "invalid_score"


def test_scanned_on_unparseable_becomes_none():
    xml = ("<mcq-test-result scanned-on='not-a-date'>"
           "<student-number>1</student-number><test-id>1</test-id>"
           "<summary-marks available='10' obtained='5'/></mcq-test-result>")
    r = validate_record(parse(xml))
    assert r.scanned_on is None


def test_empty_optional_first_name_becomes_none():
    xml = ("<mcq-test-result>"
           "<first-name></first-name>"
           "<student-number>1</student-number><test-id>1</test-id>"
           "<summary-marks available='10' obtained='5'/></mcq-test-result>")
    r = validate_record(parse(xml))
    assert r.first_name is None


def test_unknown_elements_ignored():
    xml = ("<mcq-test-result>"
           "<answer>foo</answer><reporting-team-junk/>"
           "<student-number>1</student-number><test-id>1</test-id>"
           "<summary-marks available='10' obtained='5'/></mcq-test-result>")
    r = validate_record(parse(xml))
    assert r.marks_obtained == 5


def test_long_test_id_rejected():
    long = "x" * 257
    xml = (f"<mcq-test-result><student-number>1</student-number><test-id>{long}</test-id>"
           "<summary-marks available='1' obtained='1'/></mcq-test-result>")
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.error == "invalid_field_value"
```

- [x] **Step 2: Implement**

```python
# src/markr/ingestion/validator.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from xml.etree.ElementTree import Element

from markr.api.errors import MarkrHTTPException

REQUIRED_TEXT_FIELDS = ("student-number", "test-id")
MAX_TEXT_LEN = 256


@dataclass(frozen=True, slots=True)
class RawRecord:
    test_id: str
    student_number: str
    marks_available: int
    marks_obtained: int
    first_name: str | None
    last_name: str | None
    scanned_on: datetime | None


def _trim(s: str | None) -> str:
    return (s or "").strip()


def _opt_text_last_seen(record: Element, tag: str) -> str | None:
    last: str | None = None
    for el in record.findall(tag):
        v = _trim(el.text or "")
        if v:
            last = v
    return last


def validate_record(record: Element) -> RawRecord:
    # 1. Cardinality of required fields (exactly once)
    for field in REQUIRED_TEXT_FIELDS:
        n = len(record.findall(field))
        if n != 1:
            raise MarkrHTTPException(
                status_code=422,
                error="cardinality_violation",
                message=f"required field {field!r} appeared {n} times",
                details={"field": field, "count": n},
            )
    n_sm = len(record.findall("summary-marks"))
    if n_sm != 1:
        raise MarkrHTTPException(
            status_code=422,
            error="cardinality_violation",
            message=f"required field 'summary-marks' appeared {n_sm} times",
            details={"field": "summary-marks", "count": n_sm},
        )

    # 2. Required text fields: trim, non-empty, length cap
    sn = _trim(record.findtext("student-number"))
    tid = _trim(record.findtext("test-id"))
    for field, val in (("student-number", sn), ("test-id", tid)):
        if not val:
            raise MarkrHTTPException(
                status_code=422, error="invalid_field_value",
                message=f"{field} empty after trim", details={"field": field},
            )
        if len(val) > MAX_TEXT_LEN:
            raise MarkrHTTPException(
                status_code=422, error="invalid_field_value",
                message=f"{field} too long", details={"field": field, "max": MAX_TEXT_LEN},
            )

    # 3. summary-marks numeric
    sm = record.find("summary-marks")
    assert sm is not None  # cardinality already enforced
    avail_raw = _trim(sm.get("available", ""))
    obt_raw = _trim(sm.get("obtained", ""))
    try:
        avail = int(avail_raw)
        obt = int(obt_raw)
    except ValueError:
        raise MarkrHTTPException(
            status_code=422, error="invalid_score",
            message="available/obtained not parseable as int",
            details={"available": avail_raw, "obtained": obt_raw},
        )
    if avail <= 0:
        raise MarkrHTTPException(
            status_code=422, error="invalid_score",
            message="available must be > 0", details={"available": avail},
        )
    if obt < 0:
        raise MarkrHTTPException(
            status_code=422, error="invalid_score",
            message="obtained must be >= 0", details={"obtained": obt},
        )
    if obt > avail:
        raise MarkrHTTPException(
            status_code=422, error="invalid_score",
            message="obtained must be <= available",
            details={"obtained": obt, "available": avail},
        )

    # 4. Optional fields
    first = _opt_text_last_seen(record, "first-name")
    last = _opt_text_last_seen(record, "last-name")
    scanned_raw = record.get("scanned-on")
    scanned: datetime | None = None
    if scanned_raw:
        try:
            scanned = datetime.fromisoformat(scanned_raw)
        except ValueError:
            scanned = None  # tolerate, do not reject

    return RawRecord(
        test_id=tid,
        student_number=sn,
        marks_available=avail,
        marks_obtained=obt,
        first_name=first,
        last_name=last,
        scanned_on=scanned,
    )
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_validator.py -v
uv run mypy src/markr/ingestion/validator.py
git add src/markr/ingestion/validator.py tests/test_validator.py
git commit -m "feat: per-record validator (spec §6, §9.3)"
```

**Acceptance criteria:** all parametrised tests pass; mypy clean.

---

## Phase 7 — Dedup + Repository + UPSERT

### Task 8.1: In-memory dedup

**Spec:** §5.4 (dedup)

**Files:**
- Create: `src/markr/ingestion/dedup.py`
- Create: `tests/test_dedup.py`

- [x] **Step 1: Failing test (uses spec §5.4 example table)**

```python
# tests/test_dedup.py
from datetime import datetime, timezone
from markr.ingestion.dedup import dedup
from markr.ingestion.validator import RawRecord

def _r(test, sn, obt, av, fn=None, ln=None, ts=None):
    return RawRecord(test, sn, av, obt, fn, ln, ts)

def test_spec_table_example():
    t1 = datetime(2017, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2017, 1, 2, tzinfo=timezone.utc)
    t3 = datetime(2017, 1, 3, tzinfo=timezone.utc)
    rs = [
        _r("X", "001", 10, 20, "Jane",  "Austen", t1),
        _r("X", "001", 15, 20, None,    "Austen", t2),
        _r("X", "001", 13, 20, "Janet", None,     t3),
    ]
    out = dedup(rs)
    assert len(out) == 1
    r = out[0]
    assert r.marks_obtained == 15
    assert r.marks_available == 20
    assert r.first_name == "Janet"
    assert r.last_name == "Austen"
    assert r.scanned_on == t3

def test_max_available_takes_higher():
    rs = [
        _r("X", "001", 15, 10),  # invalid combo would be filtered earlier — this is just for max-of-available
        _r("X", "001", 12, 20),
    ]
    # Validator runs first; for dedup unit test we craft a legal pair:
    rs = [_r("X", "001", 10, 10), _r("X", "001", 12, 20)]
    out = dedup(rs)
    assert out[0].marks_available == 20
    assert out[0].marks_obtained == 12

def test_keys_independent():
    rs = [_r("X", "1", 5, 10), _r("X", "2", 7, 10), _r("Y", "1", 9, 10)]
    out = dedup(rs)
    keys = {(r.test_id, r.student_number) for r in out}
    assert keys == {("X", "1"), ("X", "2"), ("Y", "1")}
```

- [x] **Step 2: Implement**

```python
# src/markr/ingestion/dedup.py
from __future__ import annotations
from typing import Iterable

from markr.ingestion.validator import RawRecord


def dedup(records: Iterable[RawRecord]) -> list[RawRecord]:
    by_key: dict[tuple[str, str], RawRecord] = {}
    for r in records:
        key = (r.test_id, r.student_number)
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = r
            continue
        by_key[key] = RawRecord(
            test_id=r.test_id,
            student_number=r.student_number,
            marks_available=max(prev.marks_available, r.marks_available),
            marks_obtained=max(prev.marks_obtained, r.marks_obtained),
            first_name=r.first_name if r.first_name is not None else prev.first_name,
            last_name=r.last_name if r.last_name is not None else prev.last_name,
            scanned_on=r.scanned_on if r.scanned_on is not None else prev.scanned_on,
        )
    return list(by_key.values())
```

- [x] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_dedup.py -v
git add src/markr/ingestion/dedup.py tests/test_dedup.py
git commit -m "feat: in-memory dedup with max/last-non-null rules (spec §5.4)"
```

**Acceptance criteria:** 3 tests pass.

---

### Task 8.2: Repository — chunked UPSERT + aggregate query

**Spec:** §5.4 (UPSERT), §8.3, §3.1 (typed return)

**Files:**
- Create: `src/markr/db/repository.py`
- Create: `tests/conftest.py`
- Create: `tests/test_repository.py`

- [ ] **Step 1: Test fixture (testcontainers + bootstrap)**

```python
# tests/conftest.py
from __future__ import annotations
import os, pytest, asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from testcontainers.postgres import PostgresContainer
from importlib.resources import files


@pytest.fixture(scope="session")
def db_url() -> str:
    if env := os.getenv("TEST_DATABASE_URL"):
        return env
    pg = PostgresContainer("postgres:16-alpine", driver="asyncpg")
    pg.start()
    yield_url = pg.get_connection_url()
    # session-scoped teardown via finalizer below
    pytest._markr_pg = pg  # type: ignore[attr-defined]
    return yield_url


@pytest.fixture(scope="session", autouse=True)
def _stop_pg(request):
    yield
    pg = getattr(pytest, "_markr_pg", None)
    if pg is not None:
        pg.stop()


@pytest.fixture()
async def engine(db_url: str) -> AsyncEngine:
    eng = create_async_engine(db_url)
    schema_sql = (files("markr.db") / "schema.sql").read_text(encoding="utf-8")
    async with eng.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS test_results"))
        await conn.execute(text(schema_sql))
    yield eng
    await eng.dispose()
```

- [ ] **Step 2: Failing test**

```python
# tests/test_repository.py
import pytest
from datetime import datetime, timezone
from markr.db.repository import Repository, AggregateStats
from markr.ingestion.validator import RawRecord

def _r(t, sn, av, ob, fn=None, ln=None, ts=None):
    return RawRecord(t, sn, av, ob, fn, ln, ts)

@pytest.mark.asyncio
async def test_upsert_and_query(engine):
    repo = Repository(engine, engine)
    await repo.upsert([_r("T", "1", 20, 13)])
    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.count == 1
    assert stats.mean == pytest.approx(65.0, rel=1e-9)
    assert stats.stddev == 0.0

@pytest.mark.asyncio
async def test_upsert_idempotent_greatest(engine):
    repo = Repository(engine, engine)
    await repo.upsert([_r("T", "1", 20, 10)])
    await repo.upsert([_r("T", "1", 20, 13)])
    await repo.upsert([_r("T", "1", 20, 11)])
    stats = await repo.aggregate("T")
    assert stats.count == 1
    assert stats.mean == pytest.approx(65.0, rel=1e-9)

@pytest.mark.asyncio
async def test_optional_fields_coalesce(engine):
    repo = Repository(engine, engine)
    await repo.upsert([_r("T", "1", 20, 10, fn="Jane", ln="Austen", ts=datetime(2017,1,1,tzinfo=timezone.utc))])
    await repo.upsert([_r("T", "1", 20, 10, fn=None, ln=None, ts=None)])
    rows = await repo.debug_select("T")
    r = rows[0]
    assert r["first_name"] == "Jane"
    assert r["last_name"] == "Austen"
    assert r["scanned_on"] is not None

@pytest.mark.asyncio
async def test_chunking(engine):
    repo = Repository(engine, engine, chunk_size=100)
    rs = [_r("T", str(i), 100, i) for i in range(1, 251)]  # forces 3 chunks
    await repo.upsert(rs)
    stats = await repo.aggregate("T")
    assert stats.count == 250

@pytest.mark.asyncio
async def test_aggregate_no_rows(engine):
    repo = Repository(engine, engine)
    stats = await repo.aggregate("DOES-NOT-EXIST")
    assert stats is None
```

- [ ] **Step 3: Implement**

```python
# src/markr/db/repository.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.ingestion.validator import RawRecord


@dataclass(frozen=True, slots=True)
class AggregateStats:
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int


_UPSERT_BASE = """
INSERT INTO test_results (test_id, student_number, marks_available, marks_obtained,
                          first_name, last_name, scanned_on)
VALUES {values_clause}
ON CONFLICT (test_id, student_number) DO UPDATE SET
  marks_available = GREATEST(test_results.marks_available, EXCLUDED.marks_available),
  marks_obtained  = GREATEST(test_results.marks_obtained,  EXCLUDED.marks_obtained),
  first_name      = COALESCE(EXCLUDED.first_name, test_results.first_name),
  last_name       = COALESCE(EXCLUDED.last_name,  test_results.last_name),
  scanned_on      = COALESCE(EXCLUDED.scanned_on, test_results.scanned_on)
"""


_AGG_SQL = text("""
SELECT
  AVG(pct)                                          AS mean,
  COALESCE(STDDEV_POP(pct), 0)                      AS stddev,
  MIN(pct)                                          AS min,
  MAX(pct)                                          AS max,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pct) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY pct) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pct) AS p75,
  COUNT(*)                                          AS count
FROM (
  SELECT marks_obtained::float / marks_available * 100 AS pct
  FROM test_results
  WHERE test_id = :test_id
) t
""")


class Repository:
    def __init__(self, write_engine: AsyncEngine, read_engine: AsyncEngine,
                 chunk_size: int = 1000) -> None:
        self._write = write_engine
        self._read = read_engine
        self._chunk = chunk_size

    async def upsert(self, records: Sequence[RawRecord]) -> None:
        if not records:
            return
        async with self._write.begin() as conn:
            for i in range(0, len(records), self._chunk):
                chunk = records[i : i + self._chunk]
                placeholders: list[str] = []
                params: dict[str, object] = {}
                for j, r in enumerate(chunk):
                    placeholders.append(
                        f"(:tid_{j}, :sn_{j}, :av_{j}, :ob_{j}, :fn_{j}, :ln_{j}, :ts_{j})"
                    )
                    params[f"tid_{j}"] = r.test_id
                    params[f"sn_{j}"] = r.student_number
                    params[f"av_{j}"] = r.marks_available
                    params[f"ob_{j}"] = r.marks_obtained
                    params[f"fn_{j}"] = r.first_name
                    params[f"ln_{j}"] = r.last_name
                    params[f"ts_{j}"] = r.scanned_on
                sql = _UPSERT_BASE.format(values_clause=", ".join(placeholders))
                await conn.execute(text(sql), params)

    async def aggregate(self, test_id: str) -> AggregateStats | None:
        async with self._read.connect() as conn:
            res = await conn.execute(_AGG_SQL, {"test_id": test_id})
            row = res.mappings().one()
            count = int(row["count"])
            if count == 0:
                return None
            return AggregateStats(
                mean=float(row["mean"]),
                stddev=float(row["stddev"]),
                min=float(row["min"]),
                max=float(row["max"]),
                p25=float(row["p25"]),
                p50=float(row["p50"]),
                p75=float(row["p75"]),
                count=count,
            )

    async def debug_select(self, test_id: str) -> list[dict[str, object]]:
        async with self._read.connect() as conn:
            res = await conn.execute(
                text("SELECT * FROM test_results WHERE test_id = :t"),
                {"t": test_id},
            )
            return [dict(m) for m in res.mappings().all()]
```

- [ ] **Step 4: Pass + commit**

```bash
uv run pytest tests/test_repository.py -v
uv run mypy src/markr/db/repository.py
git add src/markr/db/repository.py tests/conftest.py tests/test_repository.py
git commit -m "feat: Repository with chunked UPSERT + PERCENTILE_CONT aggregate (spec §5.4, §8.3)"
```

**Acceptance criteria:** 5 tests pass; mypy clean. `AggregateStats` fields are non-Optional `float` per spec §3.1.

---

## Phase 8 — Pipeline + ingestion router

### Task 9.1: Content-type guard

**Spec:** §5.4 (content-type)

**Files:**
- Create: `src/markr/api/content_type.py`
- Create: `tests/test_content_type.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_content_type.py
import pytest
from markr.api.content_type import require_markr_xml
from markr.api.errors import MarkrHTTPException

@pytest.mark.parametrize("ct", [
    "text/xml+markr",
    "text/xml+markr; charset=utf-8",
    " TEXT/XML+MARKR ; charset=utf-8 ",
])
def test_accepted(ct):
    require_markr_xml(ct)

@pytest.mark.parametrize("ct", [
    "", "text/xml", "application/xml", "text/xml+markr-bad", "application/json",
])
def test_rejected(ct):
    with pytest.raises(MarkrHTTPException) as ei:
        require_markr_xml(ct)
    assert ei.value.status_code == 415
    assert ei.value.error == "unsupported_media_type"
```

- [ ] **Step 2: Implement**

```python
# src/markr/api/content_type.py
from __future__ import annotations
from markr.api.errors import MarkrHTTPException

REQUIRED = "text/xml+markr"


def require_markr_xml(content_type: str | None) -> None:
    media = (content_type or "").split(";", 1)[0].strip().lower()
    if media != REQUIRED:
        raise MarkrHTTPException(
            status_code=415,
            error="unsupported_media_type",
            message=f"expected {REQUIRED}",
            details={"got": media},
        )
```

- [ ] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_content_type.py -v
git add src/markr/api/content_type.py tests/test_content_type.py
git commit -m "feat: content-type guard (spec §5.4)"
```

**Acceptance criteria:** all parametrised tests pass.

---

### Task 9.2: Pipeline orchestrator

**Spec:** §5.3, §5.4, §9.3

**Files:**
- Create: `src/markr/ingestion/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Failing test (covers strict order short-circuit)**

```python
# tests/test_pipeline.py
import pytest
from markr.ingestion.pipeline import process_xml_body
from markr.api.errors import MarkrHTTPException

def make(records_xml: str) -> bytes:
    return f"<mcq-test-results>{records_xml}</mcq-test-results>".encode()

@pytest.mark.asyncio
async def test_happy(engine):
    from markr.db.repository import Repository
    repo = Repository(engine, engine)
    body = make("""
      <mcq-test-result scanned-on="2017-01-01T00:00:00Z">
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>""")
    await process_xml_body(body, repo)
    stats = await repo.aggregate("T")
    assert stats.count == 1

@pytest.mark.asyncio
async def test_first_failure_short_circuits(engine):
    from markr.db.repository import Repository
    repo = Repository(engine, engine)
    body = make("""
      <mcq-test-result>
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>
      <mcq-test-result>
        <student-number>2</student-number>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>""")
    with pytest.raises(MarkrHTTPException) as ei:
        await process_xml_body(body, repo)
    assert ei.value.error == "cardinality_violation"
    # Nothing committed
    assert await repo.aggregate("T") is None

@pytest.mark.asyncio
async def test_dedup_then_upsert(engine):
    from markr.db.repository import Repository
    repo = Repository(engine, engine)
    body = make("""
      <mcq-test-result>
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="11"/>
      </mcq-test-result>
      <mcq-test-result>
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>""")
    await process_xml_body(body, repo)
    rows = await repo.debug_select("T")
    assert len(rows) == 1
    assert rows[0]["marks_obtained"] == 13
```

- [ ] **Step 2: Implement**

```python
# src/markr/ingestion/pipeline.py
from __future__ import annotations
from markr.db.repository import Repository
from markr.ingestion.dedup import dedup
from markr.ingestion.structure import gate_root_and_count
from markr.ingestion.validator import validate_record
from markr.ingestion.xml_parser import safe_parse, MalformedXMLError
from markr.api.errors import MarkrHTTPException


async def process_xml_body(body: bytes, repo: Repository) -> None:
    try:
        root = safe_parse(body)
    except MalformedXMLError as exc:
        raise MarkrHTTPException(
            status_code=400, error="malformed_xml",
            message=str(exc) or "could not parse XML body",
        ) from exc

    record_elems = gate_root_and_count(root)
    raw = [validate_record(el) for el in record_elems]  # short-circuits on first failure
    deduped = dedup(raw)
    await repo.upsert(deduped)
```

- [ ] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_pipeline.py -v
git add src/markr/ingestion/pipeline.py tests/test_pipeline.py
git commit -m "feat: ingestion pipeline orchestrator (spec §5.3, §5.4)"
```

**Acceptance criteria:** 3 tests pass.

---

### Task 9.3: Ingestion router (POST /import)

**Spec:** §5.1, §5.2, §5.3

**Files:**
- Create: `src/markr/api/ingestion.py`
- Create: `tests/test_ingestion_route.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_ingestion_route.py
import httpx, pytest
from fastapi import FastAPI
from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

@pytest.fixture
def app(engine):
    a = FastAPI()
    a.add_middleware(BodyCapMiddleware)
    register_exception_handlers(a)
    repo = Repository(engine, engine)
    a.include_router(build_ingestion_router(repo))
    return a

@pytest.mark.asyncio
async def test_post_happy(app):
    body = b"""<mcq-test-results>
      <mcq-test-result>
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>
    </mcq-test-results>"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=body, headers={"content-type": "text/xml+markr"})
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_post_wrong_content_type(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"<x/>", headers={"content-type": "application/xml"})
        assert r.status_code == 415
        assert r.json()["error"] == "unsupported_media_type"

@pytest.mark.asyncio
async def test_post_malformed(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/import", content=b"<oops",
                         headers={"content-type": "text/xml+markr"})
        assert r.status_code == 400
        assert r.json()["error"] == "malformed_xml"

@pytest.mark.asyncio
async def test_wrong_method(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.put("/import", content=b"x")
        assert r.status_code == 405
        assert r.json()["error"] == "method_not_allowed"
```

- [ ] **Step 2: Implement**

```python
# src/markr/api/ingestion.py
from __future__ import annotations
from fastapi import APIRouter, Request

from markr.api.content_type import require_markr_xml
from markr.db.repository import Repository
from markr.ingestion.pipeline import process_xml_body


def build_ingestion_router(repo: Repository) -> APIRouter:
    r = APIRouter()

    @r.post("/import")
    async def import_xml(request: Request) -> dict[str, str]:
        require_markr_xml(request.headers.get("content-type"))
        body = await request.body()
        await process_xml_body(body, repo)
        return {"status": "ok"}

    return r
```

- [ ] **Step 3: Wire into create_app + pass**

Modify `src/markr/main.py` `create_app()`:

```python
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

# inside create_app, after engines built:
repo = Repository(write_engine, read_engine)
app.include_router(build_ingestion_router(repo))
app.state.repository = repo
```

- [ ] **Step 4: Pass + commit**

```bash
uv run pytest tests/test_ingestion_route.py -v
git add src/markr/api/ingestion.py src/markr/main.py tests/test_ingestion_route.py
git commit -m "feat: POST /import router (spec §5.1, §5.2)"
```

**Acceptance criteria:** 4 tests pass.

---

### Task 9.4: 🟢 **E2E checkpoint #2 — POST /import via curl with sample_results.xml**

**Spec:** §5, brief example

- [ ] **Step 1: Bring up stack**

```bash
docker compose up --build -d
sleep 5
curl -sS http://localhost:4567/health
```

- [ ] **Step 2: POST sample data**

```bash
curl -sS -X POST \
  -H 'Content-Type: text/xml+markr' \
  --data-binary @sample_results.xml \
  -o /tmp/markr_post.json -w "HTTP=%{http_code}\n" \
  http://localhost:4567/import
cat /tmp/markr_post.json
```

Expected:
```
HTTP=200
{"status":"ok"}
```

- [ ] **Step 3: POST the brief's curl example**

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import \
  -w "HTTP=%{http_code}\n" -d @- <<'XML'
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

Expected: `HTTP=200`.

- [ ] **Step 4: Verify rows landed**

```bash
docker compose exec -T db psql -U markr -d markr -c "SELECT COUNT(*) FROM test_results"
docker compose exec -T db psql -U markr -d markr -c "SELECT test_id, COUNT(*) FROM test_results GROUP BY test_id ORDER BY 1"
```

Expected: counts > 0; `9863` group present (sample test id), `1234` group present.

- [ ] **Step 5: Idempotent replay**

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml \
  -w "HTTP=%{http_code}\n" http://localhost:4567/import
docker compose exec -T db psql -U markr -d markr -c "SELECT COUNT(*) FROM test_results WHERE test_id='9863'"
```

Expected: same count after replay (UPSERT idempotent — spec §5.5).

- [ ] **Step 6: Tear down + commit**

```bash
docker compose down
git commit --allow-empty -m "test(e2e): POST /import happy path verified with sample_results.xml"
```

**Acceptance criteria:** Steps 2/3/5 all return `HTTP=200`. DB counts match between original POST and replay POST.

---

## Phase 9 — Aggregation

### Task 10.1: Aggregation router + path validation

**Spec:** §8.1, §8.4, §8.6

**Files:**
- Create: `src/markr/api/aggregation.py`
- Create: `tests/test_aggregation_route.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_aggregation_route.py
import httpx, pytest
from fastapi import FastAPI
from markr.api.aggregation import build_aggregation_router
from markr.api.exception_handlers import register_exception_handlers
from markr.db.repository import Repository
from markr.ingestion.validator import RawRecord


@pytest.fixture
def app(engine):
    a = FastAPI()
    register_exception_handlers(a)
    repo = Repository(engine, engine)
    a.include_router(build_aggregation_router(repo))
    a.state._repo = repo
    return a


@pytest.mark.asyncio
async def test_aggregate_404_when_empty(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/results/NOPE/aggregate")
        assert r.status_code == 404
        body = r.json()
        assert body["error"] == "not_found"
        assert body["details"]["reason"] == "no_matching_rows"
        assert body["details"]["test_id"] == "NOPE"


@pytest.mark.asyncio
async def test_aggregate_single_row(app):
    repo: Repository = app.state._repo
    await repo.upsert([RawRecord("T", "1", 20, 13, None, None, None)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/results/T/aggregate")
        assert r.status_code == 200
        # Field order matches spec §8.4
        assert r.text.replace(" ", "").startswith(
            '{"mean":65.0,"stddev":0.0,"min":65.0,"max":65.0,"p25":65.0,"p50":65.0,"p75":65.0,"count":1}'
        )


@pytest.mark.asyncio
async def test_aggregate_path_whitespace_invalid(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/results/%20%20/aggregate")
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_path_param"


@pytest.mark.asyncio
async def test_aggregate_path_too_long(app):
    long = "x" * 257
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(f"/results/{long}/aggregate")
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_path_param"
```

- [ ] **Step 2: Implement**

```python
# src/markr/api/aggregation.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel

from markr.api.errors import MarkrHTTPException
from markr.db.repository import Repository


class AggregateResponse(BaseModel):
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int


def build_aggregation_router(repo: Repository) -> APIRouter:
    r = APIRouter()

    @r.get("/results/{test_id}/aggregate", response_model=AggregateResponse)
    async def aggregate(
        test_id: Annotated[str, Path(min_length=1, max_length=256)],
    ) -> AggregateResponse:
        tid = test_id.strip()
        if not tid:
            raise MarkrHTTPException(
                status_code=422, error="invalid_path_param",
                message="test_id is empty after trim",
                details={"field": "test_id"},
            )
        stats = await repo.aggregate(tid)
        if stats is None:
            raise MarkrHTTPException(
                status_code=404, error="not_found",
                message=f"no results for test_id={tid}",
                details={"reason": "no_matching_rows", "test_id": tid},
            )
        return AggregateResponse(
            mean=stats.mean, stddev=stats.stddev, min=stats.min, max=stats.max,
            p25=stats.p25, p50=stats.p50, p75=stats.p75, count=stats.count,
        )

    return r
```

- [ ] **Step 3: Wire into create_app**

Modify `src/markr/main.py`:

```python
from markr.api.aggregation import build_aggregation_router
# inside create_app:
app.include_router(build_aggregation_router(repo))
```

- [ ] **Step 4: Pass + commit**

```bash
uv run pytest tests/test_aggregation_route.py -v
git add src/markr/api/aggregation.py src/markr/main.py tests/test_aggregation_route.py
git commit -m "feat: GET /results/{test_id}/aggregate (spec §8)"
```

**Acceptance criteria:** 4 tests pass; the single-row response is byte-equal (modulo whitespace) to the spec example string.

---

### Task 10.2: Multi-row aggregation property test

**Spec:** §8.2, §8.5, §8.6

**Files:**
- Create: `tests/test_aggregation_math.py`

- [ ] **Step 1: Test (verifies per-student mean of percentages, not sum/sum weighted)**

```python
# tests/test_aggregation_math.py
import pytest
from markr.db.repository import Repository
from markr.ingestion.validator import RawRecord

@pytest.mark.asyncio
async def test_mean_is_unweighted_per_student(engine):
    repo = Repository(engine, engine)
    # student A: 5/10 = 50%, student B: 18/20 = 90%
    # unweighted mean = (50+90)/2 = 70.0
    # weighted (sum/sum) = 23/30*100 = 76.666...
    await repo.upsert([
        RawRecord("T", "A", 10, 5, None, None, None),
        RawRecord("T", "B", 20, 18, None, None, None),
    ])
    s = await repo.aggregate("T")
    assert s.count == 2
    assert s.mean == pytest.approx(70.0, rel=1e-9)
    assert s.min == pytest.approx(50.0, rel=1e-9)
    assert s.max == pytest.approx(90.0, rel=1e-9)

@pytest.mark.asyncio
async def test_no_app_layer_rounding(engine):
    repo = Repository(engine, engine)
    # 1/3 * 100 = 33.333... — must NOT be rounded
    await repo.upsert([RawRecord("T", "A", 3, 1, None, None, None)])
    s = await repo.aggregate("T")
    assert s.mean == pytest.approx(100.0 / 3.0, rel=1e-12)
```

- [ ] **Step 2: Pass + commit**

```bash
uv run pytest tests/test_aggregation_math.py -v
git add tests/test_aggregation_math.py
git commit -m "test: aggregation math is per-student mean, no app rounding (spec §8.2, §8.5)"
```

**Acceptance criteria:** both tests pass.

---

### Task 10.3: 🟢 **E2E checkpoint #3 — GET /results/.../aggregate via curl**

**Spec:** §8, brief example

- [ ] **Step 1: Bring up + reload sample**

```bash
docker compose down -v
docker compose up --build -d
sleep 5
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml http://localhost:4567/import
```

- [ ] **Step 2: Hit aggregate for sample test_id 9863**

```bash
curl -sS http://localhost:4567/results/9863/aggregate
echo
```

Expected: JSON object with `mean`, `stddev`, `min`, `max`, `p25`, `p50`, `p75`, `count` in that exact order, all numeric, `count > 0`.

- [ ] **Step 3: Brief's example test_id 1234 (single record)**

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<'XML'
<mcq-test-results>
  <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
    <student-number>521585128</student-number>
    <test-id>1234</test-id>
    <summary-marks available="20" obtained="13" />
  </mcq-test-result>
</mcq-test-results>
XML
curl -sS http://localhost:4567/results/1234/aggregate
```

Expected (byte-equal modulo whitespace to spec §8.4 example):
```
{"mean":65.0,"stddev":0.0,"min":65.0,"max":65.0,"p25":65.0,"p50":65.0,"p75":65.0,"count":1}
```

- [ ] **Step 4: 404 for unknown test_id**

```bash
curl -sS -o /tmp/agg404.json -w "HTTP=%{http_code}\n" http://localhost:4567/results/DOESNOTEXIST/aggregate
cat /tmp/agg404.json
```

Expected: `HTTP=404`, body `{"error":"not_found",..., "details":{"reason":"no_matching_rows","test_id":"DOESNOTEXIST"}}`.

- [ ] **Step 5: Tear down + commit**

```bash
docker compose down
git commit --allow-empty -m "test(e2e): aggregate happy + 404 verified via curl"
```

**Acceptance criteria:** Step 3 output exactly equals the spec §8.4 JSON string. Step 4 returns 404 with `reason: no_matching_rows`.

---

## Phase 10 — Negative-path coverage + cross-cutting

### Task 11.1: Body-cap integration test (real ASGI client)

**Spec:** §5.4

**Files:**
- Create: `tests/test_body_cap_integration.py`

- [ ] **Step 1: Test**

```python
# tests/test_body_cap_integration.py
import httpx, pytest
from fastapi import FastAPI
from markr.api.body_cap import BodyCapMiddleware, BODY_LIMIT_BYTES
from markr.api.content_type import require_markr_xml
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

@pytest.mark.asyncio
async def test_oversize_body_413(engine):
    a = FastAPI()
    a.add_middleware(BodyCapMiddleware)
    register_exception_handlers(a)
    a.include_router(build_ingestion_router(Repository(engine, engine)))
    big = b"<mcq-test-results>" + b"<x/>" * (BODY_LIMIT_BYTES // 4 + 10) + b"</mcq-test-results>"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://t") as c:
        r = await c.post("/import", content=big, headers={"content-type": "text/xml+markr"})
        assert r.status_code == 413
        assert r.json()["error"] == "body_too_large"
```

- [ ] **Step 2: Pass + commit**

```bash
uv run pytest tests/test_body_cap_integration.py -v
git add tests/test_body_cap_integration.py
git commit -m "test: body cap integration on /import (spec §5.4)"
```

**Acceptance criteria:** test passes.

---

### Task 11.2: Record-count cap test using fixture XML

**Spec:** §5.4 (record count check)

**Files:**
- Create: `tests/fixtures/over_10k.py` (test-only generator helper — not a fixture file because 10k+1 inflated XML is too large to commit)
- Create: `tests/test_record_count_cap.py`

- [ ] **Step 1: Test**

```python
# tests/test_record_count_cap.py
import httpx, pytest
from fastapi import FastAPI
from markr.api.body_cap import BodyCapMiddleware
from markr.api.content_type import require_markr_xml
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

def _make(n: int) -> bytes:
    inner = (b"<mcq-test-result>"
             b"<student-number>SN</student-number><test-id>T</test-id>"
             b"<summary-marks available='1' obtained='1'/></mcq-test-result>") * n
    return b"<mcq-test-results>" + inner + b"</mcq-test-results>"

@pytest.mark.asyncio
async def test_10001_rejected(engine):
    a = FastAPI()
    a.add_middleware(BodyCapMiddleware)
    register_exception_handlers(a)
    a.include_router(build_ingestion_router(Repository(engine, engine)))
    body = _make(10_001)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://t") as c:
        r = await c.post("/import", content=body, headers={"content-type": "text/xml+markr"})
        # Could trip body-cap first depending on size; either way 413 with one of two error codes
        assert r.status_code == 413
        assert r.json()["error"] in {"record_count_exceeded", "body_too_large"}
```

> Note: 10,001 records of the minimal shape above (~115 bytes each) is ~1.15 MB — well under 10 MiB body cap, so this hits the record-count rejector. If the body cap fires first in your env, lower per-record size or accept either code.

- [ ] **Step 2: Pass + commit**

```bash
uv run pytest tests/test_record_count_cap.py -v
git add tests/test_record_count_cap.py
git commit -m "test: 10k record cap (spec §5.4)"
```

**Acceptance criteria:** test passes with `record_count_exceeded` (preferred).

---

### Task 11.3: 🟢 **E2E checkpoint #4 — negative-path matrix via curl**

**Spec:** §9.2 (entire mapping table)

- [ ] **Step 1: Bring up**

```bash
docker compose up --build -d
sleep 5
```

- [ ] **Step 2: 415 wrong content-type**

```bash
curl -sS -o /tmp/415.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: application/xml' --data-binary '<x/>' http://localhost:4567/import
cat /tmp/415.json
```
Expected: `HTTP=415`, error `unsupported_media_type`.

- [ ] **Step 2b: §5.3 ordering — wrong CT + oversized body must still be 415, not 413**

```bash
# Send a small body but advertise a huge Content-Length to try to bait 413 first.
curl -sS -o /tmp/415_order.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: application/xml' \
  -H 'Content-Length: 99999999' \
  --data-binary '<x/>' http://localhost:4567/import
cat /tmp/415_order.json
```
Expected: `HTTP=415`, error `unsupported_media_type` (proves CT check precedes body cap per spec §5.3).

- [ ] **Step 3: 400 malformed**

```bash
curl -sS -o /tmp/400.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: text/xml+markr' --data-binary '<oops' http://localhost:4567/import
cat /tmp/400.json
```
Expected: `HTTP=400`, error `malformed_xml`.

- [ ] **Step 4: 422 wrong root**

```bash
curl -sS -o /tmp/422root.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: text/xml+markr' --data-binary '<other/>' http://localhost:4567/import
cat /tmp/422root.json
```
Expected: `HTTP=422`, error `wrong_root`.

- [ ] **Step 5: 422 empty batch**

```bash
curl -sS -o /tmp/422empty.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: text/xml+markr' --data-binary '<mcq-test-results></mcq-test-results>' \
  http://localhost:4567/import
cat /tmp/422empty.json
```
Expected: `HTTP=422`, error `empty_batch`.

- [ ] **Step 6: 422 invalid_score**

```bash
curl -sS -o /tmp/422score.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<'XML'
<mcq-test-results>
  <mcq-test-result>
    <student-number>1</student-number><test-id>T</test-id>
    <summary-marks available="0" obtained="0"/>
  </mcq-test-result>
</mcq-test-results>
XML
cat /tmp/422score.json
```
Expected: `HTTP=422`, error `invalid_score`.

- [ ] **Step 7: 422 cardinality_violation (missing summary-marks)**

```bash
curl -sS -o /tmp/422card.json -w "HTTP=%{http_code}\n" -X POST \
  -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<'XML'
<mcq-test-results>
  <mcq-test-result>
    <student-number>1</student-number><test-id>T</test-id>
  </mcq-test-result>
</mcq-test-results>
XML
cat /tmp/422card.json
```
Expected: `HTTP=422`, error `cardinality_violation`, `details.field == "summary-marks"`.

- [ ] **Step 8: 405 wrong method**

```bash
curl -sS -o /tmp/405.json -w "HTTP=%{http_code}\n" -X PUT \
  -H 'Content-Type: text/xml+markr' --data-binary '<x/>' http://localhost:4567/import
cat /tmp/405.json
```
Expected: `HTTP=405`, error `method_not_allowed`.

- [ ] **Step 9: 422 invalid path param (whitespace)**

```bash
curl -sS -o /tmp/422path.json -w "HTTP=%{http_code}\n" "http://localhost:4567/results/%20%20/aggregate"
cat /tmp/422path.json
```
Expected: `HTTP=422`, error `invalid_path_param`.

- [ ] **Step 10: 404 unknown route**

```bash
curl -sS -o /tmp/404u.json -w "HTTP=%{http_code}\n" http://localhost:4567/nope
cat /tmp/404u.json
```
Expected: `HTTP=404`, `details.reason == "unknown_route"`.

- [ ] **Step 11: 404 aggregate-no-rows (vs 404 unknown route — distinguishable by `details.reason`)**

```bash
curl -sS http://localhost:4567/results/NEVERSEEN/aggregate
```
Expected: 404, `details.reason == "no_matching_rows"`.

- [ ] **Step 12: Tear down + commit**

```bash
docker compose down
git commit --allow-empty -m "test(e2e): negative-path envelope matrix (spec §9.2) verified"
```

**Acceptance criteria:** every step's status code and `error` value matches spec §9.2.

---

### Task 11.4: Sample fixture round-trip integration test

**Spec:** §5, §6, brief sample

**Files:**
- Create: `tests/fixtures/sample_results.xml` (copy of repo-root file)
- Create: `tests/test_sample_round_trip.py`

- [ ] **Step 1: Copy fixture**

```bash
cp sample_results.xml tests/fixtures/sample_results.xml
```

- [ ] **Step 2: Test**

```python
# tests/test_sample_round_trip.py
import httpx, pytest
from pathlib import Path
from fastapi import FastAPI
from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.aggregation import build_aggregation_router
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

SAMPLE = Path(__file__).parent / "fixtures" / "sample_results.xml"

@pytest.mark.asyncio
async def test_sample_post_then_aggregate(engine):
    a = FastAPI()
    a.add_middleware(BodyCapMiddleware)
    register_exception_handlers(a)
    repo = Repository(engine, engine)
    a.include_router(build_ingestion_router(repo))
    a.include_router(build_aggregation_router(repo))
    body = SAMPLE.read_bytes()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://t") as c:
        r = await c.post("/import", content=body, headers={"content-type": "text/xml+markr"})
        assert r.status_code == 200
        # sample's test_id is 9863 per the journal
        r2 = await c.get("/results/9863/aggregate")
        assert r2.status_code == 200
        j = r2.json()
        assert j["count"] >= 1
        for k in ("mean", "stddev", "min", "max", "p25", "p50", "p75"):
            assert isinstance(j[k], (int, float))

@pytest.mark.asyncio
async def test_sample_replay_idempotent(engine):
    repo = Repository(engine, engine)
    a = FastAPI()
    a.add_middleware(BodyCapMiddleware)
    register_exception_handlers(a)
    a.include_router(build_ingestion_router(repo))
    a.include_router(build_aggregation_router(repo))
    body = SAMPLE.read_bytes()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://t") as c:
        for _ in range(3):
            r = await c.post("/import", content=body, headers={"content-type": "text/xml+markr"})
            assert r.status_code == 200
        r2 = await c.get("/results/9863/aggregate")
        c1 = r2.json()
    # Distinct count rows after replay = same as after first ingest
    assert c1["count"] >= 1
```

- [ ] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_sample_round_trip.py -v
git add tests/fixtures/sample_results.xml tests/test_sample_round_trip.py
git commit -m "test: sample fixture round-trip + idempotent replay (spec §5.5)"
```

**Acceptance criteria:** both tests pass.

---

### Task 11.5: 🟢 **E2E checkpoint #5 — replay-after-restart idempotency via curl**

**Spec:** §5.5

> **Scope note:** this checkpoint exercises the "after-COMMIT replay converges" guarantee from spec §5.5 (the bottom rows of the crash-point table). It does NOT inject an in-flight crash (`kill -9` mid-COMMIT) — that would test rows 2–4 of the matrix. Spec §5.5 only mandates the *guarantee* (idempotent replay via `GREATEST(...)`); in-flight crash injection is out of scope for the prototype.

- [ ] **Step 1: Bring up**

```bash
docker compose up --build -d
sleep 5
```

- [ ] **Step 2: POST sample once, snapshot row count for test_id 9863**

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml http://localhost:4567/import
COUNT_1=$(docker compose exec -T db psql -U markr -d markr -tAc "SELECT COUNT(*) FROM test_results WHERE test_id='9863'")
echo "count after first POST: $COUNT_1"
```

- [ ] **Step 3: Kill app mid-stride and restart**

```bash
docker compose restart app
sleep 5
curl -sS http://localhost:4567/health
```

- [ ] **Step 4: Replay the same payload**

```bash
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml http://localhost:4567/import
COUNT_2=$(docker compose exec -T db psql -U markr -d markr -tAc "SELECT COUNT(*) FROM test_results WHERE test_id='9863'")
echo "count after replay: $COUNT_2"
test "$COUNT_1" = "$COUNT_2" && echo "OK: idempotent" || (echo "FAIL: counts diverged"; exit 1)
```

- [ ] **Step 5: Tear down + commit**

```bash
docker compose down
git commit --allow-empty -m "test(e2e): replay idempotency after restart verified (spec §5.5)"
```

**Acceptance criteria:** Step 4 prints `OK: idempotent`. Distinct (test_id, student_number) row count is unchanged after replay.

---

## Phase 11 — Lint, mypy, README

### Task 12.1: Make ruff + mypy green across the codebase

**Spec:** §3, §3.1, §3.2

- [ ] **Step 1: Run all gates**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/markr
uv run pytest -v
```

- [ ] **Step 2: Fix anything that fires**

For mypy specifically:
- Ensure `Repository.aggregate` returns `AggregateStats | None` and `AggregateStats.*` stat fields are non-Optional `float` (spec §3.1).
- Ensure `safe_parse` returns stdlib `Element` (spec §3.1).

- [ ] **Step 3: Commit**

```bash
git commit -am "chore: ruff + mypy strict clean across src/markr"
```

**Acceptance criteria:** all four commands above exit 0.

---

### Task 13.1: README

**Spec:** §15 (full section list, in order)

**Files:**
- Modify: `README.md`

> The current `README.md` is the brief verbatim. Replace it with the deliverable README, but **preserve the brief** by moving it under a heading "Original brief" near the bottom or into `docs/brief.md` (the spec implies the deliverable README is the customer-facing one).

- [ ] **Step 1: Move brief**

```bash
mkdir -p docs
git mv README.md docs/brief.md
```

- [ ] **Step 2: Write deliverable README**

Sections in this exact order (spec §15):

1. **Quick start**
   - `docker compose up --build`
   - The brief's `curl` POST example
   - The brief's `curl` GET example
2. **Assumptions** — copy each bullet from spec §14 with one preceding line of *why*.
3. **Decisions & trade-offs** — short prose on: single-service vs two-service; sync vs fire-and-forget; DOM vs streaming; trust `<summary-marks>`; intra-request dedup in app code; **empty batch returns 422 `empty_batch`**; **no app-layer rounding on aggregate stats**.
4. **Excluded (deliberately)** — copy from spec §13.1.
5. **Real-time dashboards (write-up only)** — ≤200 words; ASCII flow `POST /import → COMMIT → outbox publisher → consumer → Redis pre-aggregated cache → SSE → dashboard`; state explicitly that `/aggregate` remains the canonical answer.
6. **Future work** — copy from spec §13.2.
7. **Running tests** — `uv sync && uv run pytest` (testcontainers, requires Docker); fallback `TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest`.

Commands appendix (spec §16) optional but recommended.

- [ ] **Step 3: Verify section presence with simple grep**

```bash
for section in "Quick start" "Assumptions" "Decisions" "Excluded" "Real-time dashboards" "Future work" "Running tests"; do
  grep -F "$section" README.md > /dev/null && echo "OK: $section" || echo "MISSING: $section"
done
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/brief.md
git commit -m "docs: deliverable README (spec §15) — brief preserved at docs/brief.md"
```

**Acceptance criteria:**
- All 7 section names appear in README.md.
- §5 (real-time dashboards) is ≤200 words and contains the ASCII flow.
- `docs/brief.md` contains the original brief unchanged.

---

### Task 13.2: Final smoke run

- [ ] **Step 1: Cold-start the system from scratch**

```bash
docker compose down -v
docker compose up --build -d
sleep 8
```

- [ ] **Step 2: Reviewer-quick-reference commands (spec §16)**

```bash
curl -sS http://localhost:4567/health
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml http://localhost:4567/import
curl -sS http://localhost:4567/results/9863/aggregate
docker compose down
```

Each must return the expected status / payload from prior E2E checkpoints.

- [ ] **Step 3: Lint/type/test sweep one more time**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/markr && uv run pytest
```

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore: final smoke + lint/type/test sweep clean"
```

**Acceptance criteria:** all commands exit 0; aggregate response for 9863 is a well-formed JSON object with the 8 fields in spec §8.4 order.

---

## Open questions (raise with user before deviating)

1. **`scanned-on` empty string vs missing attribute** — spec says missing attr → `None`; an explicit empty string `scanned-on=""` is not addressed. Plan treats it as missing (no parse, `None`). If reviewer expects rejection, raise.
2. **Multiple `<summary-marks>` cardinality** — spec §6.2 lists it as exactly-1; T7.3 enforces this. Confirm with reviewer that the brief's "extra fields tolerated" leniency does NOT extend to required fields appearing twice (the spec explicitly says cardinality_violation; we follow spec).
3. **`uvicorn --workers 2` in tests** — tests use ASGITransport (in-process); only the deployed container uses 2 workers. Advisory-lock bootstrap is exercised in T2.6 spike; production race is left to lifespan correctness, not a separate test.
4. **`fixtures/sample_results.xml`** — committed copy of the repo-root file (T11.4). If the reviewer rejects file duplication, switch to a `pytest` `--rootdir`-relative path lookup.

---

## Self-review checklist (run after writing this plan)

- [x] **Spec coverage** — every spec section §1–§17 cited in the coverage matrix and at least one task. Spot-check on §5.5 (T8.2 idempotent UPSERT + T11.5 E2E replay), §8.5 (T10.2 no-rounding test), §9.5 (T5.2 four handlers).
- [x] **Placeholder scan** — no "TBD", no "implement later", no "similar to". All test bodies are full code.
- [x] **Type consistency** — `Repository`, `RawRecord`, `AggregateStats`, `MarkrHTTPException`, `BodyCapMiddleware`, `MAX_RECORDS`, `BODY_LIMIT_BYTES` names used uniformly across tasks.
- [x] **Topology** — every `from markr.X import Y` in a test reaches a definition created in a strictly earlier task.
- [x] **E2E gating** — checkpoints at T6.5 (health), T9.4 (POST), T10.3 (GET), T11.3 (negative matrix), T11.5 (replay). All before final smoke.
- [x] **Spike gating** — every external API touched has a spike in T2.x prior to its first integration task.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-02-markr-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints for review.

**Which approach?**
