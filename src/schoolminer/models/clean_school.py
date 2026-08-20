from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Ownership = Literal[
    "PUBLIC",
    "PRIVATE",
    "UNKNOWN",
]


RegionNormalizationStatus = Literal[
    "NORMALIZED",
    "NEEDS_REVIEW",
    "MISSING",
]


class CleanPhone(BaseModel):
    """One phone value derived from a raw directory phone field."""

    model_config = ConfigDict(
        extra="forbid",
    )

    raw: str
    normalized: Optional[str] = None


class CleanLocation(BaseModel):
    """Source-preserving and normalized school location."""

    model_config = ConfigDict(
        extra="forbid",
    )

    region_raw: Optional[str] = None
    region: Optional[str] = None

    region_status: RegionNormalizationStatus

    town_raw: Optional[str] = None
    town: Optional[str] = None


class CleanDirectorySchool(BaseModel):
    """Deterministically cleaned school listing."""

    model_config = ConfigDict(
        extra="forbid",
    )

    source: str
    source_detail_id: str

    name_raw: str
    name: str

    ownership_raw: Optional[int] = None
    ownership: Ownership

    location: CleanLocation

    phone_raw: Optional[str] = None

    phones: List[CleanPhone] = Field(default_factory=list)
