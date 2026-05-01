import httpx
import pytest
from fastapi import FastAPI

from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository


def _records(count: int) -> bytes:
    record = (
        b"<mcq-test-result>"
        b"<student-number>SN</student-number>"
        b"<test-id>T</test-id>"
        b"<summary-marks available='1' obtained='1'/>"
        b"</mcq-test-result>"
    )
    return b"<mcq-test-results>" + (record * count) + b"</mcq-test-results>"


@pytest.mark.asyncio
async def test_10001_import_records_returns_record_count_exceeded(engine):
    app = FastAPI()
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    app.include_router(build_ingestion_router(Repository(engine, engine)))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://t",
    ) as client:
        response = await client.post(
            "/import",
            content=_records(10_001),
            headers={"content-type": "text/xml+markr"},
        )

    assert response.status_code == 413
    assert response.json()["error"] == "record_count_exceeded"
