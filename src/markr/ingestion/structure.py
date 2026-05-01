from __future__ import annotations

from xml.etree.ElementTree import Element

from markr.api.errors import MarkrHTTPException

ROOT_TAG = "mcq-test-results"
RECORD_TAG = "mcq-test-result"
MAX_RECORDS = 10_000


def gate_root_and_count(root: Element) -> list[Element]:
    if root.tag != ROOT_TAG:
        raise MarkrHTTPException(
            status_code=422,
            error="wrong_root",
            message=f"unexpected root element: {root.tag!r}",
            details={"got": root.tag, "expected": ROOT_TAG},
        )

    records = root.findall(RECORD_TAG)
    count = len(records)
    if count > MAX_RECORDS:
        raise MarkrHTTPException(
            status_code=413,
            error="record_count_exceeded",
            message=f"batch contains {count} records (limit {MAX_RECORDS})",
            details={"count": count, "limit": MAX_RECORDS},
        )
    if count == 0:
        raise MarkrHTTPException(
            status_code=422,
            error="empty_batch",
            message="document contains zero records",
        )
    return records
