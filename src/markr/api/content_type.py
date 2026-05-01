from __future__ import annotations

from markr.api.errors import MarkrHTTPException

REQUIRED = "text/xml+markr"


def require_markr_xml(content_type: str | None) -> None:
    media = (content_type or "").split(";", 1)[0].strip().lower()
    if media != REQUIRED:
        raise MarkrHTTPException(
            status_code=415,
            error="unsupported_media_type",
            message=f"expected {REQUIRED}",
            details={"got": media},
        )
