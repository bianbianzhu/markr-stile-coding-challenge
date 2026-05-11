import pytest

from markr.db.repository import Repository
from markr.ingestion.validator import RawRecord


@pytest.mark.asyncio
async def test_mean_is_unweighted_per_student(engine):
    repo = Repository(engine, engine)

    await repo.upsert(
        [
            RawRecord("T", "A", 10, 5, None, None, None),
            RawRecord("T", "B", 20, 18, None, None, None),
        ]
    )

    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.count == 2
    # MAX(available) per test_id = 20: A=5/20=25%, B=18/20=90%, mean=57.5.
    assert stats.mean == pytest.approx(57.5, rel=1e-9)
    assert stats.min == pytest.approx(25.0, rel=1e-9)
    assert stats.max == pytest.approx(90.0, rel=1e-9)


@pytest.mark.asyncio
async def test_aggregate_uses_test_level_max_available(engine):
    repo = Repository(engine, engine)

    await repo.upsert(
        [
            RawRecord("T", "A", 10, 5, None, None, None),
            RawRecord("T", "B", 11, 5, None, None, None),
        ]
    )

    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.count == 2
    expected = 5 / 11 * 100
    assert stats.mean == pytest.approx(expected, rel=1e-12)
    assert stats.min == pytest.approx(expected, rel=1e-12)
    assert stats.max == pytest.approx(expected, rel=1e-12)
    assert stats.p25 == pytest.approx(expected, rel=1e-12)
    assert stats.p50 == pytest.approx(expected, rel=1e-12)
    assert stats.p75 == pytest.approx(expected, rel=1e-12)
    assert stats.stddev == pytest.approx(0.0, abs=1e-12)


@pytest.mark.asyncio
async def test_no_app_layer_rounding(engine):
    repo = Repository(engine, engine)

    await repo.upsert([RawRecord("T", "A", 3, 1, None, None, None)])

    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.mean == pytest.approx(100.0 / 3.0, rel=1e-12)
