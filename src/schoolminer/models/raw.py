from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RawDirectoryRecord(BaseModel):
    """One immutable source record captured during a directory crawl."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str
    source: str
    category: str
    region_filter: str
    page: int
    position: int
    fetched_at: datetime
    source_detail_id: str
    source_url: str
    detail_url: str
    raw: dict[str, Any]
