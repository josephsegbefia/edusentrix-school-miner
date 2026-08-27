from __future__ import annotations

from typing import Optional

from schoolminer.cleaning.locations import normalize_region
from schoolminer.cleaning.placeholders import clean_source_value
from schoolminer.models.enriched_school import GeographyStatus

# These mappings are deliberately limited to district
# labels that we have actually observed in the source
# and have enough evidence to resolve to a modern region.
#
# We are resolving the REGION only.
#
# We are NOT claiming that an old district label is the
# same thing as a current district. For example:
#
#   Pru District
#
# was later divided, but both resulting districts are in
# Bono East, so the modern REGION can still be determined
# safely.
DISTRICT_REGION_MAP = {
    # -------------------------------------------------
    # Historical Bono / Brong-Ahafo source geography
    # -------------------------------------------------
    "asunafo north": "Ahafo",
    "asunafo south": "Ahafo",
    "berekum": "Bono",
    "dormaa municipal": "Bono",
    "jaman south district": "Bono",
    "sunyani municipal": "Bono",
    "sunyani west": "Bono",
    "nkoranza south district": "Bono East",
    "pru district": "Bono East",
    # -------------------------------------------------
    # Northern
    # -------------------------------------------------
    "tamale district": "Northern",
    # -------------------------------------------------
    # Historical Volta source geography
    # -------------------------------------------------
    #
    # Adaklu-Anyigbe later ceased to exist in this form.
    # Its successor geography remains within modern
    # Volta, so the REGION is still safely resolvable.
    "adaklu-anyigbe": "Volta",
    "keta": "Volta",
    "ketu south municipal": "Volta",
    "krachi east district": "Oti",
    "nkwanta north district": "Oti",
    "nkwanta south district": "Oti",
    # -------------------------------------------------
    # Historical Western source geography
    # -------------------------------------------------
    "ahanta west district": "Western",
    # Historical Aowin-Suaman geography now falls
    # within Western North.
    "aowin suaman district": "Western North",
    "ellembelle": "Western",
    "prestea huni valley": "Western",
    "sefwi wiawso district": "Western North",
    "shama district": "Western",
    "wasa amenfi east": "Western",
    "wasa amenfi east district": "Western",
    "wasa amenfi west district": "Western",
}


def _district_key(
    value: Optional[str],
) -> Optional[str]:
    """
    Produce a conservative lookup key for a source
    district value.

    We normalize whitespace/case only. We deliberately
    do not strip words such as District or Municipal,
    because doing so globally could create false matches.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return None

    return cleaned.casefold()


def region_for_district(
    district_raw: Optional[str],
) -> Optional[str]:
    """
    Return a modern canonical region for a known source
    district label.

    Unknown district labels remain unresolved.
    """

    key = _district_key(district_raw)

    if key is None:
        return None

    return DISTRICT_REGION_MAP.get(key)


def resolve_canonical_region(
    region_raw: Optional[str],
    district_raw: Optional[str],
) -> tuple[
    Optional[str],
    GeographyStatus,
    Optional[str],
]:
    """
    Resolve modern Ghana region using source region and
    district evidence.

    Resolution order:

    1. Normalize an unambiguous source region.
    2. Compare against district evidence when available.
    3. Resolve ambiguous/missing historical region labels
       from a known district.
    4. Otherwise require review instead of guessing.

    Returns:
        canonical_region,
        geography_status,
        region_resolution_basis
    """

    cleaned_region = clean_source_value(region_raw)

    cleaned_district = clean_source_value(district_raw)

    direct_region, direct_status = normalize_region(cleaned_region)

    district_region = region_for_district(cleaned_district)

    # -------------------------------------------------
    # Source region is independently unambiguous.
    # -------------------------------------------------

    if direct_status == "NORMALIZED":
        # If we ALSO understand the district and it
        # contradicts the source region, do not silently
        # choose one.
        if district_region is not None and district_region != direct_region:
            return (
                None,
                "NEEDS_REVIEW",
                (f"region/district conflict: {cleaned_region} / {cleaned_district}"),
            )

        return (
            direct_region,
            "NORMALIZED",
            cleaned_region,
        )

    # -------------------------------------------------
    # The source region is historical/ambiguous or
    # absent, but the district safely identifies a
    # modern region.
    # -------------------------------------------------

    if district_region is not None:
        return (
            district_region,
            "RESOLVED_FROM_DISTRICT",
            cleaned_district,
        )

    # -------------------------------------------------
    # No region and no useful district evidence.
    # -------------------------------------------------

    if direct_status == "MISSING" and cleaned_district is None:
        return (
            None,
            "MISSING",
            None,
        )

    # -------------------------------------------------
    # We have some source geography, but not enough
    # evidence to resolve it safely.
    # -------------------------------------------------

    return (
        None,
        "NEEDS_REVIEW",
        (cleaned_district or cleaned_region),
    )
