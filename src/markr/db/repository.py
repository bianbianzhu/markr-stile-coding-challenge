from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.ingestion.validator import RawRecord


@dataclass(frozen=True, slots=True)
class AggregateStats:
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int


_UPSERT_BASE = """
INSERT INTO test_results (
  test_id, student_number, marks_available, marks_obtained,
  first_name, last_name, scanned_on
)
VALUES {values_clause}
ON CONFLICT (test_id, student_number) DO UPDATE SET
  marks_available = GREATEST(test_results.marks_available, EXCLUDED.marks_available),
  marks_obtained  = GREATEST(test_results.marks_obtained,  EXCLUDED.marks_obtained),
  first_name      = COALESCE(EXCLUDED.first_name, test_results.first_name),
  last_name       = COALESCE(EXCLUDED.last_name,  test_results.last_name),
  scanned_on      = COALESCE(EXCLUDED.scanned_on, test_results.scanned_on)
"""

_AGG_SQL = text(
    """
SELECT
  AVG(pct)                                          AS mean,
  COALESCE(STDDEV_POP(pct), 0)                      AS stddev,
  MIN(pct)                                          AS min,
  MAX(pct)                                          AS max,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pct) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY pct) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pct) AS p75,
  COUNT(*)                                          AS count
FROM (
  SELECT marks_obtained::float / MAX(marks_available) OVER () * 100 AS pct
  FROM test_results
  WHERE test_id = :test_id
) t
"""
)


class Repository:
    def __init__(
        self,
        write_engine: AsyncEngine,
        read_engine: AsyncEngine,
        chunk_size: int = 1000,
    ) -> None:
        self._write = write_engine
        self._read = read_engine
        self._chunk_size = chunk_size

    async def upsert(self, records: Sequence[RawRecord]) -> None:
        if not records:
            return

        async with self._write.begin() as conn:
            for start in range(0, len(records), self._chunk_size):
                chunk = records[start : start + self._chunk_size]
                placeholders: list[str] = []
                params: dict[str, object] = {}
                for index, record in enumerate(chunk):
                    placeholders.append(
                        f"(:test_id_{index}, :student_number_{index}, "
                        f":marks_available_{index}, :marks_obtained_{index}, "
                        f":first_name_{index}, :last_name_{index}, :scanned_on_{index})"
                    )
                    params[f"test_id_{index}"] = record.test_id
                    params[f"student_number_{index}"] = record.student_number
                    params[f"marks_available_{index}"] = record.marks_available
                    params[f"marks_obtained_{index}"] = record.marks_obtained
                    params[f"first_name_{index}"] = record.first_name
                    params[f"last_name_{index}"] = record.last_name
                    params[f"scanned_on_{index}"] = record.scanned_on

                sql = _UPSERT_BASE.format(values_clause=", ".join(placeholders))
                await conn.execute(text(sql), params)

    async def aggregate(self, test_id: str) -> AggregateStats | None:
        async with self._read.connect() as conn:
            result = await conn.execute(_AGG_SQL, {"test_id": test_id})
            row = result.mappings().one()

        count = int(row["count"])
        if count == 0:
            return None

        return AggregateStats(
            mean=float(row["mean"]),
            stddev=float(row["stddev"]),
            min=float(row["min"]),
            max=float(row["max"]),
            p25=float(row["p25"]),
            p50=float(row["p50"]),
            p75=float(row["p75"]),
            count=count,
        )

    async def debug_select(self, test_id: str) -> list[dict[str, object]]:
        async with self._read.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM test_results WHERE test_id = :test_id"),
                {"test_id": test_id},
            )
            return [dict(row) for row in result.mappings().all()]
