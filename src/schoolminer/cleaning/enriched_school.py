from __future__ import annotations

from schoolminer.cleaning.emails import (
    clean_email,
)
from schoolminer.cleaning.enriched_phones import (
    reconcile_phones,
)
from schoolminer.cleaning.geography import (
    resolve_canonical_region,
)
from schoolminer.cleaning.ownership import (
    normalize_ownership,
)
from schoolminer.cleaning.profile import (
    normalize_assistance_needed,
    normalize_detail_ownership,
    normalize_gender,
    normalize_levels,
    normalize_profile_text,
)
from schoolminer.cleaning.text import (
    clean_required_text,
)
from schoolminer.models.directory_detail import (
    DirectoryDetail,
)
from schoolminer.models.enriched_school import (
    DetailSourceData,
    EnrichedLocation,
    EnrichedSchoolCandidate,
    ListingSourceData,
)
from schoolminer.models.raw import (
    RawDirectoryRecord,
)


def _string_value(
    value: object,
):
    if isinstance(
        value,
        str,
    ):
        return value

    return None


def _integer_value(
    value: object,
):
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


def build_enriched_school_candidate(
    listing: RawDirectoryRecord,
    detail: DirectoryDetail,
) -> EnrichedSchoolCandidate:
    """
    Build one processed school candidate from a unique
    listing record and its parsed detail page.

    Raw source values are retained separately from
    normalized values.
    """

    if listing.source_detail_id != detail.source_detail_id:
        raise ValueError("Listing and detail source IDs do not match.")

    raw = listing.raw

    name_raw = _string_value(raw.get("InstitutionName"))

    name = clean_required_text(
        name_raw,
        field_name="InstitutionName",
    )

    listing_town_raw = _string_value(raw.get("TownName"))

    listing_region_raw = _string_value(raw.get("Region"))

    listing_phone_raw = _string_value(raw.get("Phone"))

    ownership_id_raw = _integer_value(raw.get("OwnerShipId"))

    logo_raw = _string_value(raw.get("Logo"))

    listing_ownership = normalize_ownership(ownership_id_raw)

    detail_ownership = normalize_detail_ownership(detail.ownership_raw)

    review_reasons = []

    if (
        listing_ownership != "UNKNOWN"
        and detail_ownership != "UNKNOWN"
        and listing_ownership != detail_ownership
    ):
        review_reasons.append("OWNERSHIP_CONFLICT")

    if listing_ownership != "UNKNOWN":
        ownership = listing_ownership

    else:
        ownership = detail_ownership

    gender = normalize_gender(detail.gender_raw)

    levels = normalize_levels(detail.levels_raw)

    phones = reconcile_phones(
        listing_phone_raw,
        detail.phone_raw,
    )

    email = clean_email(detail.email_raw)

    if email.status == "INVALID":
        review_reasons.append("INVALID_EMAIL")

    head_name = normalize_profile_text(detail.head_name_raw)

    postal_address = normalize_profile_text(detail.postal_address_raw)

    town = normalize_profile_text(listing_town_raw)

    location = normalize_profile_text(detail.location_raw)

    district = normalize_profile_text(detail.district_raw)

    source_region = normalize_profile_text(detail.region_raw) or normalize_profile_text(
        listing_region_raw
    )

    (
        canonical_region,
        geography_status,
        region_resolution_basis,
    ) = resolve_canonical_region(
        source_region,
        district,
    )

    if geography_status in {
        "NEEDS_REVIEW",
        "MISSING",
    }:
        review_reasons.append("UNRESOLVED_GEOGRAPHY")

    assistance_needed = normalize_assistance_needed(detail.assistance_needed_raw)

    return EnrichedSchoolCandidate(
        source=listing.source,
        source_detail_id=(listing.source_detail_id),
        displayed_school_id=(normalize_profile_text(detail.displayed_school_id)),
        listing=ListingSourceData(
            name_raw=name_raw,
            town_raw=listing_town_raw,
            region_raw=(listing_region_raw),
            phone_raw=(listing_phone_raw),
            ownership_id_raw=(ownership_id_raw),
            logo_raw=logo_raw,
        ),
        detail=DetailSourceData(
            displayed_school_id_raw=(detail.displayed_school_id),
            displayed_name_raw=(detail.displayed_name),
            ownership_raw=(detail.ownership_raw),
            gender_raw=(detail.gender_raw),
            levels_raw=list(detail.levels_raw),
            region_raw=(detail.region_raw),
            head_name_raw=(detail.head_name_raw),
            phone_raw=(detail.phone_raw),
            location_raw=(detail.location_raw),
            postal_address_raw=(detail.postal_address_raw),
            email_raw=(detail.email_raw),
            district_raw=(detail.district_raw),
            assistance_needed_raw=(detail.assistance_needed_raw),
        ),
        name=name,
        ownership=ownership,
        gender=gender,
        levels=levels,
        phones=phones,
        email=email,
        head_name=head_name,
        postal_address=(postal_address),
        assistance_needed=(assistance_needed),
        location=EnrichedLocation(
            town=town,
            location=location,
            district=district,
            canonical_region=(canonical_region),
            geography_status=(geography_status),
            region_resolution_basis=(region_resolution_basis),
        ),
        review_required=bool(review_reasons),
        review_reasons=(review_reasons),
    )
