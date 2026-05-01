import httpx
import pytest
from fastapi import FastAPI

from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ingestion import build_ingestion_router
from markr.db.repository import Repository


@pytest.fixture
def app(engine):
    app = FastAPI()
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    repo = Repository(engine, engine)
    app.include_router(build_ingestion_router(repo))
    return app


@pytest.mark.asyncio
async def test_post_happy(app):
    body = b"""<mcq-test-results>
      <mcq-test-result>
        <student-number>1</student-number><test-id>T</test-id>
        <summary-marks available="20" obtained="13"/>
      </mcq-test-result>
    </mcq-test-results>"""

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.post(
            "/import",
            content=body,
            headers={"content-type": "text/xml+markr"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_post_wrong_content_type(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.post(
            "/import",
            content=b"<x/>",
            headers={"content-type": "application/xml"},
        )

    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_media_type"


@pytest.mark.asyncio
async def test_post_malformed(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.post(
            "/import",
            content=b"<oops",
            headers={"content-type": "text/xml+markr"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "malformed_xml"


@pytest.mark.asyncio
async def test_wrong_method(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.put("/import", content=b"x")

    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"
