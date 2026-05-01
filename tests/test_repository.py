from datetime import datetime, timezone

import pytest

from markr.db.repository import AggregateStats, Repository
from markr.ingestion.validator import RawRecord


def _r(
    test_id: str,
    student_number: str,
    available: int,
    obtained: int,
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


@pytest.mark.asyncio
async def test_upsert_and_aggregate_single_row(engine):
    repo = Repository(engine, engine)

    await repo.upsert([_r("T", "1", 20, 13)])
    stats = await repo.aggregate("T")

    assert isinstance(stats, AggregateStats)
    assert stats.count == 1
    assert stats.mean == pytest.approx(65.0, rel=1e-9)
    assert stats.stddev == 0.0
    assert stats.min == pytest.approx(65.0, rel=1e-9)
    assert stats.max == pytest.approx(65.0, rel=1e-9)
    assert stats.p25 == pytest.approx(65.0, rel=1e-9)
    assert stats.p50 == pytest.approx(65.0, rel=1e-9)
    assert stats.p75 == pytest.approx(65.0, rel=1e-9)


@pytest.mark.asyncio
async def test_upsert_idempotent_greatest_across_multiple_upserts(engine):
    repo = Repository(engine, engine)

    await repo.upsert([_r("T", "1", 20, 10)])
    await repo.upsert([_r("T", "1", 20, 13)])
    await repo.upsert([_r("T", "1", 20, 11)])
    stats = await repo.aggregate("T")

    assert stats is not None
    assert stats.count == 1
    assert stats.mean == pytest.approx(65.0, rel=1e-9)


@pytest.mark.asyncio
async def test_optional_fields_coalesce(engine):
    repo = Repository(engine, engine)
    ts = datetime(2017, 1, 1, tzinfo=timezone.utc)

    await repo.upsert([_r("T", "1", 20, 10, first_name="Jane", last_name="Austen", scanned_on=ts)])
    await repo.upsert([_r("T", "1", 20, 10)])
    await repo.upsert([_r("T", "1", 20, 10, first_name="Janet")])
    rows = await repo.debug_select("T")

    assert len(rows) == 1
    assert rows[0]["first_name"] == "Janet"
    assert rows[0]["last_name"] == "Austen"
    assert rows[0]["scanned_on"] is not None


@pytest.mark.asyncio
async def test_chunking_with_250_rows(engine):
    repo = Repository(engine, engine, chunk_size=100)
    records = [_r("T", str(i), 300, i) for i in range(1, 251)]

    await repo.upsert(records)
    stats = await repo.aggregate("T")

    assert stats is not None
    assert stats.count == 250


@pytest.mark.asyncio
async def test_aggregate_no_rows_returns_none(engine):
    repo = Repository(engine, engine)

    stats = await repo.aggregate("DOES-NOT-EXIST")

    assert stats is None
