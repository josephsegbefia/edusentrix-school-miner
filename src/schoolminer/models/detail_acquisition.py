from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DetailAcquisitionResult(BaseModel):
    """Summary of one detail acquisition invocation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str

    candidates_total: int = Field(
        ge=0,
    )

    completed_this_run: int = Field(
        ge=0,
    )

    completed_total: int = Field(
        ge=0,
    )

    remaining_total: int = Field(
        ge=0,
    )
