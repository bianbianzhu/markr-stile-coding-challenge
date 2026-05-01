import httpx
import pytest
from fastapi import FastAPI, Request

from markr.api.body_cap import BODY_LIMIT_BYTES, BodyCapMiddleware


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.post("/import")
    async def import_results(req: Request) -> dict[str, int]:
        return {"len": len(await req.body())}

    @app.post("/x")
    async def other_route(req: Request) -> dict[str, int]:
        return {"len": len(await req.body())}

    app.add_middleware(BodyCapMiddleware)
    return app


@pytest.mark.asyncio
async def test_under_limit_with_correct_ct_returns_200(app: FastAPI) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/import",
            content=b"a" * 100,
            headers={"content-type": "text/xml+markr"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_wrong_content_type_with_oversized_content_length_returns_415(
    app: FastAPI,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/import",
            content=b"a",
            headers={
                "content-type": "application/xml",
                "content-length": str(BODY_LIMIT_BYTES + 1),
            },
        )

    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_media_type"


@pytest.mark.asyncio
async def test_content_length_over_limit_with_correct_ct_returns_413(app: FastAPI) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/import",
            content=b"a",
            headers={
                "content-type": "text/xml+markr",
                "content-length": str(BODY_LIMIT_BYTES + 1),
            },
        )

    assert response.status_code == 413
    assert response.json()["error"] == "body_too_large"


@pytest.mark.asyncio
async def test_streaming_overflow_with_lying_content_length_returns_413(
    app: FastAPI,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/import",
            content=b"a" * (BODY_LIMIT_BYTES + 10),
            headers={"content-type": "text/xml+markr", "content-length": "10"},
        )

    assert response.status_code == 413
    assert response.json()["error"] == "body_too_large"


@pytest.mark.asyncio
async def test_non_import_route_not_gated_returns_200(app: FastAPI) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/x", content=b"a" * 100)

    assert response.status_code == 200
