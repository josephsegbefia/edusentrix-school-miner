from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schoolminer.models.clean_school import Ownership

ValueSource = Literal[
    "LISTING",
    "DETAIL",
    "LISTING_AND_DETAIL",
]


EmailStatus = Literal[
    "VALID",
    "INVALID",
    "MISSING",
]


GeographyStatus = Literal[
    "NORMALIZED",
    "RESOLVED_FROM_DISTRICT",
    "NEEDS_REVIEW",
    "MISSING",
]


class ListingSourceData(BaseModel):
    """Original values observed in the listing API."""

    model_config = ConfigDict(
        extra="forbid",
    )

    name_raw: str

    town_raw: Optional[str] = None
    region_raw: Optional[str] = None
    phone_raw: Optional[str] = None

    ownership_id_raw: Optional[int] = None
    logo_raw: Optional[str] = None


class DetailSourceData(BaseModel):
    """Original values parsed from the source detail page."""

    model_config = ConfigDict(
        extra="forbid",
    )

    displayed_school_id_raw: Optional[str] = None
    displayed_name_raw: Optional[str] = None

    ownership_raw: Optional[str] = None
    gender_raw: Optional[str] = None

    levels_raw: list[str] = Field(default_factory=list)

    region_raw: Optional[str] = None

    head_name_raw: Optional[str] = None
    phone_raw: Optional[str] = None
    location_raw: Optional[str] = None
    postal_address_raw: Optional[str] = None
    email_raw: Optional[str] = None
    district_raw: Optional[str] = None
    assistance_needed_raw: Optional[str] = None


class EnrichedPhone(BaseModel):
    """One normalized phone number with source provenance."""

    model_config = ConfigDict(
        extra="forbid",
    )

    normalized: Optional[str] = None

    listing_raw: Optional[str] = None
    detail_raw: Optional[str] = None

    source: ValueSource


class EnrichedEmail(BaseModel):
    """Cleaned email value and its quality state."""

    model_config = ConfigDict(
        extra="forbid",
    )

    raw: Optional[str] = None
    normalized: Optional[str] = None

    status: EmailStatus

    source: Literal["DETAIL"] = "DETAIL"


class EnrichedLocation(BaseModel):
    """Normalized geography while retaining source geography."""

    model_config = ConfigDict(
        extra="forbid",
    )

    town: Optional[str] = None
    location: Optional[str] = None
    district: Optional[str] = None

    canonical_region: Optional[str] = None

    geography_status: GeographyStatus

    region_resolution_basis: Optional[str] = None


class EnrichedSchoolCandidate(BaseModel):
    """
    One unique source school enriched with listing and
    detail-page information.

    This is a processed candidate, not yet an EduSentrix
    production prospect.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    # Stable source identity.
    source: str
    source_detail_id: str

    # Additional ID displayed by the website.
    # It is metadata only and is NOT assumed unique.
    displayed_school_id: Optional[str] = None

    # Full source provenance.
    listing: ListingSourceData
    detail: DetailSourceData

    # Normalized school identity/profile.
    name: str
    ownership: Ownership

    gender: Optional[str] = None

    levels: list[str] = Field(default_factory=list)

    # Normalized contact/profile information.
    phones: list[EnrichedPhone] = Field(default_factory=list)

    email: EnrichedEmail

    head_name: Optional[str] = None
    postal_address: Optional[str] = None

    assistance_needed: list[str] = Field(default_factory=list)

    location: EnrichedLocation

    # Quality/control metadata.
    review_required: bool = False

    review_reasons: list[str] = Field(default_factory=list)
