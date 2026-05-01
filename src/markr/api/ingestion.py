from __future__ import annotations

from fastapi import APIRouter, Request

from markr.api.content_type import require_markr_xml
from markr.db.repository import Repository
from markr.ingestion.pipeline import process_xml_body


def build_ingestion_router(repo: Repository) -> APIRouter:
    router = APIRouter()

    @router.post("/import")
    async def import_xml(request: Request) -> dict[str, str]:
        require_markr_xml(request.headers.get("content-type"))
        await process_xml_body(await request.body(), repo)
        return {"status": "ok"}

    return router
