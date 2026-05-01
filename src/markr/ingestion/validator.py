from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from xml.etree.ElementTree import Element

from markr.api.errors import MarkrHTTPException

REQUIRED_TEXT_FIELDS = ("student-number", "test-id")
MAX_TEXT_LEN = 256


@dataclass(frozen=True, slots=True)
class RawRecord:
    test_id: str
    student_number: str
    marks_available: int
    marks_obtained: int
    first_name: str | None
    last_name: str | None
    scanned_on: datetime | None


def _trim(text: str | None) -> str:
    return (text or "").strip()


def _optional_last_non_empty(record: Element, tag: str) -> str | None:
    value: str | None = None
    for element in record.findall(tag):
        text = _trim(element.text)
        if text:
            value = text
    return value


def validate_record(record: Element) -> RawRecord:
    for field in REQUIRED_TEXT_FIELDS:
        count = len(record.findall(field))
        if count != 1:
            raise MarkrHTTPException(
                status_code=422,
                error="cardinality_violation",
                message=f"required field {field!r} appeared {count} times",
                details={"field": field, "count": count},
            )

    summary_count = len(record.findall("summary-marks"))
    if summary_count != 1:
        raise MarkrHTTPException(
            status_code=422,
            error="cardinality_violation",
            message=f"required field 'summary-marks' appeared {summary_count} times",
            details={"field": "summary-marks", "count": summary_count},
        )

    student_number = _trim(record.findtext("student-number"))
    test_id = _trim(record.findtext("test-id"))
    for field, value in (("student-number", student_number), ("test-id", test_id)):
        if not value:
            raise MarkrHTTPException(
                status_code=422,
                error="invalid_field_value",
                message=f"{field} empty after trim",
                details={"field": field},
            )
        if len(value) > MAX_TEXT_LEN:
            raise MarkrHTTPException(
                status_code=422,
                error="invalid_field_value",
                message=f"{field} too long",
                details={"field": field, "max": MAX_TEXT_LEN},
            )

    summary = record.find("summary-marks")
    assert summary is not None
    available_raw = _trim(summary.get("available"))
    obtained_raw = _trim(summary.get("obtained"))
    try:
        marks_available = int(available_raw)
        marks_obtained = int(obtained_raw)
    except ValueError:
        raise MarkrHTTPException(
            status_code=422,
            error="invalid_score",
            message="available/obtained not parseable as int",
            details={"available": available_raw, "obtained": obtained_raw},
        ) from None

    if marks_available <= 0:
        raise MarkrHTTPException(
            status_code=422,
            error="invalid_score",
            message="available must be > 0",
            details={"available": marks_available},
        )
    if marks_obtained < 0:
        raise MarkrHTTPException(
            status_code=422,
            error="invalid_score",
            message="obtained must be >= 0",
            details={"obtained": marks_obtained},
        )
    if marks_obtained > marks_available:
        raise MarkrHTTPException(
            status_code=422,
            error="invalid_score",
            message="obtained must be <= available",
            details={"obtained": marks_obtained, "available": marks_available},
        )

    scanned_on: datetime | None = None
    scanned_raw = _trim(record.get("scanned-on"))
    if scanned_raw:
        try:
            scanned_on = datetime.fromisoformat(scanned_raw)
        except ValueError:
            scanned_on = None

    return RawRecord(
        test_id=test_id,
        student_number=student_number,
        marks_available=marks_available,
        marks_obtained=marks_obtained,
        first_name=_optional_last_non_empty(record, "first-name"),
        last_name=_optional_last_non_empty(record, "last-name"),
        scanned_on=scanned_on,
    )
