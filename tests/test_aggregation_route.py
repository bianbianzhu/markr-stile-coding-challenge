import httpx
import pytest
from fastapi import FastAPI

from markr.api.aggregation import build_aggregation_router
from markr.api.exception_handlers import register_exception_handlers
from markr.db.repository import Repository
from markr.ingestion.validator import RawRecord


@pytest.fixture
def app(engine):
    app = FastAPI()
    register_exception_handlers(app)
    repo = Repository(engine, engine)
    app.include_router(build_aggregation_router(repo))
    app.state.repo = repo
    return app


@pytest.mark.asyncio
async def test_aggregate_404_when_empty(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.get("/results/NOPE/aggregate")

    body = response.json()
    assert response.status_code == 404
    assert body["error"] == "not_found"
    assert body["details"]["reason"] == "no_matching_rows"
    assert body["details"]["test_id"] == "NOPE"


@pytest.mark.asyncio
async def test_aggregate_single_row_exact_field_order(app):
    repo = app.state.repo
    await repo.upsert([RawRecord("T", "1", 20, 13, None, None, None)])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.get("/results/T/aggregate")

    assert response.status_code == 200
    assert response.text.replace(" ", "") == (
        '{"mean":65.0,"stddev":0.0,"min":65.0,"max":65.0,'
        '"p25":65.0,"p50":65.0,"p75":65.0,"count":1}'
    )


@pytest.mark.asyncio
async def test_aggregate_path_whitespace_invalid(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.get("/results/%20%20/aggregate")

    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "invalid_path_param"
    assert body["details"]["field"] == "test_id"


@pytest.mark.asyncio
async def test_aggregate_path_too_long(app):
    long = "x" * 257

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.get(f"/results/{long}/aggregate")

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_path_param"
