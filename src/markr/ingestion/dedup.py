from __future__ import annotations

from collections.abc import Iterable

from markr.ingestion.validator import RawRecord


def dedup(records: Iterable[RawRecord]) -> list[RawRecord]:
    by_key: dict[tuple[str, str], RawRecord] = {}
    for record in records:
        key = (record.test_id, record.student_number)
        previous = by_key.get(key)
        if previous is None:
            by_key[key] = record
            continue

        by_key[key] = RawRecord(
            test_id=record.test_id,
            student_number=record.student_number,
            marks_available=max(previous.marks_available, record.marks_available),
            marks_obtained=max(previous.marks_obtained, record.marks_obtained),
            first_name=record.first_name if record.first_name is not None else previous.first_name,
            last_name=record.last_name if record.last_name is not None else previous.last_name,
            scanned_on=record.scanned_on if record.scanned_on is not None else previous.scanned_on,
        )
    return list(by_key.values())
