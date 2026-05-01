from datetime import datetime, timezone

from markr.ingestion.dedup import dedup
from markr.ingestion.validator import RawRecord


def _r(
    test_id: str,
    student_number: str,
    obtained: int,
    available: int,
    first_name: str | None = None,
    last_name: str | None = None,
    scanned_on: datetime | None = None,
) -> RawRecord:
    return RawRecord(
        test_id=test_id,
        student_number=student_number,
        marks_available=available,
        marks_obtained=obtained,
        first_name=first_name,
        last_name=last_name,
        scanned_on=scanned_on,
    )


def test_spec_table_example():
    t1 = datetime(2017, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2017, 1, 2, tzinfo=timezone.utc)
    t3 = datetime(2017, 1, 3, tzinfo=timezone.utc)
    rs = [
        _r("X", "001", 10, 20, "Jane", "Austen", t1),
        _r("X", "001", 15, 20, None, "Austen", t2),
        _r("X", "001", 13, 20, "Janet", None, t3),
    ]

    out = dedup(rs)

    assert len(out) == 1
    r = out[0]
    assert r.marks_obtained == 15
    assert r.marks_available == 20
    assert r.first_name == "Janet"
    assert r.last_name == "Austen"
    assert r.scanned_on == t3


def test_max_available_takes_higher():
    out = dedup([_r("X", "001", 10, 10), _r("X", "001", 12, 20)])

    assert out[0].marks_available == 20
    assert out[0].marks_obtained == 12


def test_keys_independent():
    rs = [_r("X", "1", 5, 10), _r("X", "2", 7, 10), _r("Y", "1", 9, 10)]

    out = dedup(rs)

    assert [(r.test_id, r.student_number) for r in out] == [("X", "1"), ("X", "2"), ("Y", "1")]
