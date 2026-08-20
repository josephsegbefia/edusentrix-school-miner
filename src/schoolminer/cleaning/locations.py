from __future__ import annotations

from typing import Optional

from schoolminer.cleaning.text import (
    clean_text,
)
from schoolminer.models.clean_school import (
    RegionNormalizationStatus,
)

UNAMBIGUOUS_REGION_MAP = {
    "ashanti region": "Ashanti",
    "ashanti": "Ashanti",
    "central region": "Central",
    "central": "Central",
    "eastern region": "Eastern",
    "eastern": "Eastern",
    "greater accra region": "Greater Accra",
    "greater accra": "Greater Accra",
    "upper east region": "Upper East",
    "upper east": "Upper East",
    "upper west region": "Upper West",
    "upper west": "Upper West",
    "bono region": "Bono",
    "bono": "Bono",
}


AMBIGUOUS_HISTORICAL_REGIONS = {
    "brong-ahafo region",
    "brong ahafo region",
    "northern region",
    "volta region",
    "western region",
}


def normalize_region(
    value: Optional[str],
) -> tuple[
    Optional[str],
    RegionNormalizationStatus,
]:
    """Normalize a source region only when the mapping is safe."""

    cleaned = clean_text(value)

    if cleaned is None:
        return (
            None,
            "MISSING",
        )

    lookup_value = cleaned.casefold()

    canonical = UNAMBIGUOUS_REGION_MAP.get(lookup_value)

    if canonical is not None:
        return (
            canonical,
            "NORMALIZED",
        )

    if lookup_value in AMBIGUOUS_HISTORICAL_REGIONS:
        return (
            None,
            "NEEDS_REVIEW",
        )

    return (
        None,
        "NEEDS_REVIEW",
    )
