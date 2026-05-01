import pytest

from markr.api.errors import MarkrHTTPException
from markr.db.repository import Repository
from markr.ingestion.pipeline import process_xml_body


def make(records_xml: str) -> bytes:
    return f"<mcq-test-results>{records_xml}</mcq-test-results>".encode()


@pytest.mark.asyncio
async def test_happy_inserts_and_aggregates_count(engine):
    repo = Repository(engine, engine)
    body = make(
        """
        <mcq-test-result scanned-on="2017-01-01T00:00:00+00:00">
          <student-number>1</student-number>
          <test-id>T</test-id>
          <summary-marks available="20" obtained="13"/>
        </mcq-test-result>
        """
    )

    await process_xml_body(body, repo)

    stats = await repo.aggregate("T")
    assert stats is not None
    assert stats.count == 1


@pytest.mark.asyncio
async def test_first_failure_short_circuits_and_commits_nothing(engine):
    repo = Repository(engine, engine)
    body = make(
        """
        <mcq-test-result>
          <student-number>1</student-number>
          <test-id>T</test-id>
          <summary-marks available="20" obtained="13"/>
        </mcq-test-result>
        <mcq-test-result>
          <student-number>2</student-number>
          <summary-marks available="20" obtained="13"/>
        </mcq-test-result>
        """
    )

    with pytest.raises(MarkrHTTPException) as exc_info:
        await process_xml_body(body, repo)

    assert exc_info.value.error == "cardinality_violation"
    assert await repo.aggregate("T") is None


@pytest.mark.asyncio
async def test_dedup_then_upsert_one_row_with_highest_score(engine):
    repo = Repository(engine, engine)
    body = make(
        """
        <mcq-test-result>
          <student-number>1</student-number>
          <test-id>T</test-id>
          <summary-marks available="20" obtained="11"/>
        </mcq-test-result>
        <mcq-test-result>
          <student-number>1</student-number>
          <test-id>T</test-id>
          <summary-marks available="20" obtained="13"/>
        </mcq-test-result>
        """
    )

    await process_xml_body(body, repo)

    rows = await repo.debug_select("T")
    assert len(rows) == 1
    assert rows[0]["marks_obtained"] == 13
