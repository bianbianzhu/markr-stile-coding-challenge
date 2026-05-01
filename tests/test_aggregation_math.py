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
    assert stats.mean == pytest.approx(70.0, rel=1e-9)
    assert stats.min == pytest.approx(50.0, rel=1e-9)
    assert stats.max == pytest.approx(90.0, rel=1e-9)


@pytest.mark.asyncio
async def test_no_app_layer_rounding(engine):
    repo = Repository(engine, engine)

    await repo.upsert([RawRecord("T", "A", 3, 1, None, None, None)])

    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.mean == pytest.approx(100.0 / 3.0, rel=1e-12)
