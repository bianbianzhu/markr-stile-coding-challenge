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
    async def markr(_req: Request, exc: MarkrHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": "route not found",
                    "details": {"reason": "unknown_route"},
                },
            )
        if exc.status_code == 405:
            return JSONResponse(
                status_code=405,
                content={
                    "error": "method_not_allowed",
                    "message": "method not allowed",
                    "details": {},
                },
            )

        log.warning(
            "unhandled starlette exception escaped to envelope: status=%s detail=%s",
            exc.status_code,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "internal_error",
                "message": "an unexpected framework error occurred",
                "details": {},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_path_param",
                "message": "request validation failed",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled(_req: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "internal server error", "details": {}},
        )
