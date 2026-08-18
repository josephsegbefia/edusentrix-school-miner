from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CrawlStatus = Literal[
    "PENDING",
    "RUNNING",
    "PAUSED",
    "COMPLETED",
    "FAILED",
]


PageStatus = Literal[
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
]


class CrawlJob(BaseModel):
    """Persistent state for one crawl of a directory source."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str
    source: str
    category: str
    region_filter: str

    status: CrawlStatus

    created_at: datetime
    updated_at: datetime

    total_pages: Optional[int] = Field(
        default=None,
        ge=1,
    )

    next_page: int = Field(
        default=1,
        ge=1,
    )

    records_saved: int = Field(
        default=0,
        ge=0,
    )

    last_error: Optional[str] = None


class CrawlPage(BaseModel):
    """Checkpoint state for one page inside a crawl."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str

    page_number: int = Field(
        ge=1,
    )

    status: PageStatus

    attempts: int = Field(
        default=0,
        ge=0,
    )

    records_saved: int = Field(
        default=0,
        ge=0,
    )

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    last_error: Optional[str] = None
