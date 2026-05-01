from typing import Annotated

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Path

from markr.api.errors import MarkrHTTPException
from markr.api.exception_handlers import register_exception_handlers


@pytest.fixture
def app() -> FastAPI:
    a = FastAPI()
    register_exception_handlers(a)

    @a.get("/markr")
    async def markr() -> None:
        raise MarkrHTTPException(422, "wrong_root", "bad root", {"got": "x"})

    @a.get("/boom")
    async def boom() -> None:
        raise RuntimeError("kaboom")

    @a.get("/teapot")
    async def teapot() -> None:
        raise HTTPException(status_code=418, detail="teapot")

    @a.get("/p/{x}")
    async def path_param(x: Annotated[str, Path(max_length=3)]) -> dict[str, str]:
        return {"x": x}

    return a


@pytest.mark.asyncio
async def test_markr_handler(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/markr")

    assert r.status_code == 422
    assert r.json() == {"error": "wrong_root", "message": "bad root", "details": {"got": "x"}}


@pytest.mark.asyncio
async def test_unknown_route_404(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/nope")

    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"
    assert body["details"]["reason"] == "unknown_route"


@pytest.mark.asyncio
async def test_method_not_allowed(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/markr")

    assert r.status_code == 405
    assert r.json()["error"] == "method_not_allowed"


@pytest.mark.asyncio
async def test_unhandled_framework_http_exception_maps_to_500(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/teapot")

    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"


@pytest.mark.asyncio
async def test_request_validation(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/p/toolong")

    assert r.status_code == 422
    assert r.json()["error"] == "invalid_path_param"


@pytest.mark.asyncio
async def test_unhandled_exception_500(app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/boom")

    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"
