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
