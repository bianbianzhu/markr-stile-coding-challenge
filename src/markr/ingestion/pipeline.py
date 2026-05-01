from __future__ import annotations

from markr.api.errors import MarkrHTTPException
from markr.db.repository import Repository
from markr.ingestion.dedup import dedup
from markr.ingestion.structure import gate_root_and_count
from markr.ingestion.validator import validate_record
from markr.ingestion.xml_parser import MalformedXMLError, safe_parse


async def process_xml_body(body: bytes, repo: Repository) -> None:
    try:
        root = safe_parse(body)
    except MalformedXMLError as exc:
        raise MarkrHTTPException(
            status_code=400,
            error="malformed_xml",
            message=str(exc) or "could not parse XML body",
        ) from exc

    record_elems = gate_root_and_count(root)
    records = [validate_record(record) for record in record_elems]
    await repo.upsert(dedup(records))
