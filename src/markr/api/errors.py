from __future__ import annotations

from fastapi import HTTPException


class MarkrHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.error = error
        self.message = message
        self.details = details or {}
