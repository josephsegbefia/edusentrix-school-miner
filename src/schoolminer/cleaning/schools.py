from __future__ import annotations

from typing import Optional

from schoolminer.cleaning.locations import (
    normalize_region,
)
from schoolminer.cleaning.ownership import (
    normalize_ownership,
)
from schoolminer.cleaning.phones import (
    clean_phone_field,
)
from schoolminer.cleaning.text import (
    clean_required_text,
    clean_text,
)
from schoolminer.models.clean_school import (
    CleanDirectorySchool,
    CleanLocation,
)
from schoolminer.models.raw import (
    RawDirectoryRecord,
)


def _string_value(
    value: object,
) -> Optional[str]:
    """Return a source value only when it is text."""

    if isinstance(
        value,
        str,
    ):
        return value

    return None


def _integer_value(
    value: object,
) -> Optional[int]:
    """Return a source value only when it is an integer."""

    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        int,
    ):
        return value

    return None


def clean_directory_school(
    record: RawDirectoryRecord,
) -> CleanDirectorySchool:
    """Deterministically clean one raw directory listing."""

    raw = record.raw

    name_raw = _string_value(raw.get("InstitutionName"))

    name = clean_required_text(
        name_raw,
        field_name="InstitutionName",
    )

    region_raw = _string_value(raw.get("Region"))

    region, region_status = normalize_region(region_raw)

    town_raw = _string_value(raw.get("TownName"))

    town = clean_text(town_raw)

    phone_raw = _string_value(raw.get("Phone"))

    ownership_raw = _integer_value(raw.get("OwnerShipId"))

    return CleanDirectorySchool(
        source=record.source,
        source_detail_id=(record.source_detail_id),
        name_raw=name_raw,
        name=name,
        ownership_raw=(ownership_raw),
        ownership=normalize_ownership(ownership_raw),
        location=CleanLocation(
            region_raw=region_raw,
            region=region,
            region_status=(region_status),
            town_raw=town_raw,
            town=town,
        ),
        phone_raw=phone_raw,
        phones=clean_phone_field(phone_raw),
    )
