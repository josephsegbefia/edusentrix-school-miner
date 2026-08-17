from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DirectoryListing(BaseModel):
    """One school listing returned by Ghana Education Directory."""

    model_config = ConfigDict(
        extra="allow",
    )

    institution_id: int = Field(
        alias="InstitutionId",
    )

    institution_name: str = Field(
        alias="InstitutionName",
    )

    town_name: Optional[str] = Field(
        default=None,
        alias="TownName",
    )

    region: Optional[str] = Field(
        default=None,
        alias="Region",
    )

    phone_raw: Optional[str] = Field(
        default=None,
        alias="Phone",
    )

    ownership_id: Optional[int] = Field(
        default=None,
        alias="OwnerShipId",
    )

    logo_raw: Optional[str] = Field(
        default=None,
        alias="Logo",
    )


class DirectorySearchPage(BaseModel):
    """One page returned by the structured directory search endpoint."""

    model_config = ConfigDict(
        extra="allow",
    )

    records: list[DirectoryListing] = Field(
        alias="Data",
    )

    page_count: int = Field(
        alias="PageCount",
    )
