import httpx
import pytest
from fastapi import FastAPI

from markr.api.body_cap import BODY_LIMIT_BYTES, BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository


@pytest.mark.asyncio
async def test_oversize_import_body_returns_413(engine):
    app = FastAPI()
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    app.include_router(build_ingestion_router(Repository(engine, engine)))
    body = b"<mcq-test-results>" + (b"<x/>" * (BODY_LIMIT_BYTES // 4 + 10))
    body += b"</mcq-test-results>"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://t",
    ) as client:
        response = await client.post(
            "/import",
            content=body,
            headers={"content-type": "text/xml+markr"},
        )

    assert response.status_code == 413
    assert response.json()["error"] == "body_too_large"
