from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DirectoryDetail(BaseModel):
    """Raw fields parsed from one directory detail page."""

    model_config = ConfigDict(
        extra="forbid",
    )

    source_detail_id: str

    displayed_school_id: Optional[str] = None
    displayed_name: Optional[str] = None

    ownership_raw: Optional[str] = None
    gender_raw: Optional[str] = None

    levels_raw: List[str] = Field(default_factory=list)

    region_raw: Optional[str] = None

    head_name_raw: Optional[str] = None
    phone_raw: Optional[str] = None
    location_raw: Optional[str] = None
    postal_address_raw: Optional[str] = None
    email_raw: Optional[str] = None
    district_raw: Optional[str] = None
    assistance_needed_raw: Optional[str] = None
