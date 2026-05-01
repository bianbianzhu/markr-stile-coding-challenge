from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from markr.api.aggregation import build_aggregation_router
from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository

SAMPLE = Path(__file__).parent / "fixtures" / "sample_results.xml"
EXPECTED_9863 = {
    "mean": 50.80246913580247,
    "stddev": 9.921195359439231,
    "min": 30.0,
    "max": 75.0,
    "p25": 45.0,
    "p50": 50.0,
    "p75": 55.00000000000001,
    "count": 81,
}


def _app(engine) -> FastAPI:
    app = FastAPI()
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    repo = Repository(engine, engine)
    app.include_router(build_ingestion_router(repo))
    app.include_router(build_aggregation_router(repo))
    return app


@pytest.mark.asyncio
async def test_sample_post_then_aggregate_9863(engine):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(engine)),
        base_url="http://t",
    ) as client:
        imported = await client.post(
            "/import",
            content=SAMPLE.read_bytes(),
            headers={"content-type": "text/xml+markr"},
        )
        aggregate = await client.get("/results/9863/aggregate")

    assert imported.status_code == 200
    assert aggregate.status_code == 200
    body = aggregate.json()
    assert body["count"] == EXPECTED_9863["count"]
    for key in ("mean", "stddev", "min", "max", "p25", "p50", "p75"):
        assert body[key] == pytest.approx(EXPECTED_9863[key])


@pytest.mark.asyncio
async def test_sample_replay_keeps_aggregate_count(engine):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(engine)),
        base_url="http://t",
    ) as client:
        first = await client.post(
            "/import",
            content=SAMPLE.read_bytes(),
            headers={"content-type": "text/xml+markr"},
        )
        aggregate_after_first = (await client.get("/results/9863/aggregate")).json()

        for _ in range(2):
            replay = await client.post(
                "/import",
                content=SAMPLE.read_bytes(),
                headers={"content-type": "text/xml+markr"},
            )
            assert replay.status_code == 200

        aggregate_after_replays = (await client.get("/results/9863/aggregate")).json()

    assert first.status_code == 200
    assert aggregate_after_first["count"] == EXPECTED_9863["count"]
    assert aggregate_after_replays == aggregate_after_first
