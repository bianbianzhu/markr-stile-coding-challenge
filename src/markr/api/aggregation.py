from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel

from markr.api.errors import MarkrHTTPException
from markr.db.repository import Repository


class AggregateResponse(BaseModel):
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int


def build_aggregation_router(repo: Repository) -> APIRouter:
    router = APIRouter()

    @router.get("/results/{test_id}/aggregate", response_model=AggregateResponse)
    async def aggregate(
        test_id: Annotated[str, Path(min_length=1, max_length=256)],
    ) -> AggregateResponse:
        trimmed = test_id.strip()
        if not trimmed:
            raise MarkrHTTPException(
                status_code=422,
                error="invalid_path_param",
                message="test_id is empty after trim",
                details={"field": "test_id"},
            )
        if "\x00" in trimmed:
            raise MarkrHTTPException(
                status_code=422,
                error="invalid_path_param",
                message="test_id contains NUL",
                details={"field": "test_id"},
            )

        stats = await repo.aggregate(trimmed)
        if stats is None:
            raise MarkrHTTPException(
                status_code=404,
                error="not_found",
                message=f"no results for test_id={trimmed}",
                details={"reason": "no_matching_rows", "test_id": trimmed},
            )

        return AggregateResponse.model_validate(stats, from_attributes=True)

    return router
