from __future__ import annotations

import json
from typing import Iterable, cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

BODY_LIMIT_BYTES = 10 * 1024 * 1024
REQUIRED_CT = "text/xml+markr"
GATED_PATH = "/import"
GATED_METHOD = "POST"

class _BodyTooLarge(Exception):
    pass


def _header(scope: Scope, name: bytes) -> bytes | None:
    headers = cast(Iterable[tuple[bytes, bytes]], scope.get("headers", ()))
    for key, value in headers:
        if key == name:
            return value
    return None


class BodyCapMiddleware:
    def __init__(self, app: ASGIApp, limit: int = BODY_LIMIT_BYTES) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        gated = scope.get("method") == GATED_METHOD and scope.get("path") == GATED_PATH
        if not gated:
            await self.app(scope, receive, send)
            return

        content_type = (_header(scope, b"content-type") or b"").decode("latin-1")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != REQUIRED_CT:
            await self._reject_415(send, media_type)
            return

        content_length = _header(scope, b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.limit:
                    await self._reject_413(send)
                    return
            except ValueError:
                pass

        seen = 0

        async def capped_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.limit:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, capped_receive, send)
        except _BodyTooLarge:
            await self._reject_413(send)

    async def _reject_413(self, send: Send) -> None:
        await self._write_json(
            send,
            413,
            {
                "error": "body_too_large",
                "message": f"request body exceeds {self.limit} bytes",
                "details": {"limit": self.limit},
            },
        )

    async def _reject_415(self, send: Send, got: str) -> None:
        await self._write_json(
            send,
            415,
            {
                "error": "unsupported_media_type",
                "message": f"expected {REQUIRED_CT}",
                "details": {"got": got},
            },
        )

    async def _write_json(self, send: Send, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
