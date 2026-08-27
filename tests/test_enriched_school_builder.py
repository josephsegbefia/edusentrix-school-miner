from datetime import datetime, timezone

import pytest

from schoolminer.cleaning.enriched_school import (
    build_enriched_school_candidate,
)
from schoolminer.models.directory_detail import (
    DirectoryDetail,
)
from schoolminer.models.raw import (
    RawDirectoryRecord,
)


def build_listing(
    *,
    source_detail_id: str = "1109",
    name: str = "1 SIGNAL REGIMENT BASIC",
    region: str = "Greater Accra Region",
    town: str = "Burma Camp, Accra",
    phone: str = ("0302773029 or 0244826894"),
    ownership_id: int = 2,
) -> RawDirectoryRecord:
    return RawDirectoryRecord(
        crawl_id="test-crawl",
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=1,
        position=1,
        fetched_at=datetime(
            2026,
            8,
            27,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        source_detail_id=(source_detail_id),
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": name,
            "InstitutionId": int(source_detail_id),
            "TownName": town,
            "Region": region,
            "Phone": phone,
            "OwnerShipId": ownership_id,
            "Logo": ("https://example.com/logo.png"),
        },
    )


def build_detail(
    *,
    source_detail_id: str = "1109",
) -> DirectoryDetail:
    return DirectoryDetail(
        source_detail_id=(source_detail_id),
        displayed_school_id="3959",
        displayed_name=("1 SIGNAL REGIMENT BASIC"),
        ownership_raw="Public",
        gender_raw="Mixed",
        levels_raw=[
            "Primary",
            "Junior High School",
        ],
        region_raw=("Greater Accra Region"),
        head_name_raw=("Mr. Awuku Larbi"),
        phone_raw=("0302773029 or 0244826894"),
        location_raw=("Burma Camp, Accra"),
        postal_address_raw=("P. O. Box 251"),
        email_raw="N/A",
        district_raw="Accra Metro",
        assistance_needed_raw=("Water, Library, Science Lab"),
    )


def test_build_enriched_school_candidate() -> None:
    candidate = build_enriched_school_candidate(
        build_listing(),
        build_detail(),
    )

    assert candidate.source_detail_id == "1109"

    assert candidate.displayed_school_id == "3959"

    assert candidate.name == "1 SIGNAL REGIMENT BASIC"

    assert candidate.ownership == "PUBLIC"

    assert candidate.gender == "Mixed"

    assert candidate.levels == [
        "Primary",
        "Junior High School",
    ]

    assert len(candidate.phones) == 2

    assert candidate.email.status == "MISSING"

    assert candidate.location.canonical_region == "Greater Accra"

    assert candidate.location.geography_status == "NORMALIZED"

    assert candidate.review_required is False

    assert candidate.review_reasons == []


def test_builder_resolves_historical_geography() -> None:
    listing = build_listing(
        region="Western Region",
    )

    detail = build_detail()

    detail = detail.model_copy(
        update={
            "region_raw": "Western Region",
            "district_raw": "Sefwi Wiawso District",
        }
    )

    candidate = build_enriched_school_candidate(
        listing,
        detail,
    )

    assert candidate.location.canonical_region == "Western North"

    assert candidate.location.geography_status == "RESOLVED_FROM_DISTRICT"

    assert candidate.review_required is False


def test_builder_marks_invalid_email_for_review() -> None:
    detail = build_detail().model_copy(update={"email_raw": "felixgyawa.vra.com"})

    candidate = build_enriched_school_candidate(
        build_listing(),
        detail,
    )

    assert candidate.email.status == "INVALID"

    assert candidate.review_required is True

    assert "INVALID_EMAIL" in candidate.review_reasons


def test_builder_rejects_mismatched_source_ids() -> None:
    with pytest.raises(
        ValueError,
        match="source IDs",
    ):
        build_enriched_school_candidate(
            build_listing(source_detail_id="1109"),
            build_detail(source_detail_id="9543"),
        )


def test_builder_flags_ownership_conflict() -> None:
    detail = build_detail().model_copy(
        update={
            "ownership_raw": "Private",
        }
    )

    candidate = build_enriched_school_candidate(
        build_listing(ownership_id=2),
        detail,
    )

    assert candidate.ownership == "PUBLIC"

    assert candidate.review_required is True

    assert "OWNERSHIP_CONFLICT" in candidate.review_reasons
