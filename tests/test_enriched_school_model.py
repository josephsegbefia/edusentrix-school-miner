import pytest
from pydantic import ValidationError

from schoolminer.models.enriched_school import (
    DetailSourceData,
    EnrichedEmail,
    EnrichedLocation,
    EnrichedPhone,
    EnrichedSchoolCandidate,
    ListingSourceData,
)


def build_candidate() -> EnrichedSchoolCandidate:
    return EnrichedSchoolCandidate(
        source="ghana_education_directory",
        source_detail_id="1109",
        displayed_school_id="3959",
        listing=ListingSourceData(
            name_raw=("1 SIGNAL REGIMENT BASIC"),
            town_raw=("Burma Camp, Accra"),
            region_raw=("Greater Accra Region"),
            phone_raw=("0302773029 or 0244826894"),
            ownership_id_raw=2,
            logo_raw=("https://example.com/1109.png"),
        ),
        detail=DetailSourceData(
            displayed_school_id_raw=("3959"),
            displayed_name_raw=("1 SIGNAL REGIMENT BASIC"),
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
            assistance_needed_raw=("Water, Library, BDT Workshop, Science Lab, Pavement Blocks"),
        ),
        name=("1 SIGNAL REGIMENT BASIC"),
        ownership="PUBLIC",
        gender="Mixed",
        levels=[
            "Primary",
            "Junior High School",
        ],
        phones=[
            EnrichedPhone(
                normalized=("+233302773029"),
                listing_raw=("0302773029"),
                detail_raw=("0302773029"),
                source=("LISTING_AND_DETAIL"),
            ),
            EnrichedPhone(
                normalized=("+233244826894"),
                listing_raw=("0244826894"),
                detail_raw=("0244826894"),
                source=("LISTING_AND_DETAIL"),
            ),
        ],
        email=EnrichedEmail(
            raw="N/A",
            normalized=None,
            status="MISSING",
        ),
        head_name=("Mr. Awuku Larbi"),
        postal_address=("P. O. Box 251"),
        assistance_needed=[
            "Water",
            "Library",
            "BDT Workshop",
            "Science Lab",
            "Pavement Blocks",
        ],
        location=EnrichedLocation(
            town="Burma Camp, Accra",
            location=("Burma Camp, Accra"),
            district="Accra Metro",
            canonical_region=("Greater Accra"),
            geography_status=("NORMALIZED"),
            region_resolution_basis=("Greater Accra Region"),
        ),
        review_required=False,
        review_reasons=[],
    )


def test_enriched_school_candidate_preserves_identity() -> None:
    candidate = build_candidate()

    assert candidate.source_detail_id == "1109"

    assert candidate.displayed_school_id == "3959"

    assert candidate.source == "ghana_education_directory"


def test_enriched_school_candidate_preserves_source_data() -> None:
    candidate = build_candidate()

    assert candidate.listing.phone_raw == "0302773029 or 0244826894"

    assert candidate.detail.phone_raw == "0302773029 or 0244826894"

    assert candidate.detail.email_raw == "N/A"

    assert candidate.detail.district_raw == "Accra Metro"


def test_enriched_phone_records_source_provenance() -> None:
    candidate = build_candidate()

    first_phone = candidate.phones[0]

    assert first_phone.normalized == "+233302773029"

    assert first_phone.source == "LISTING_AND_DETAIL"

    assert first_phone.listing_raw == "0302773029"

    assert first_phone.detail_raw == "0302773029"


def test_enriched_candidate_can_record_missing_email() -> None:
    candidate = build_candidate()

    assert candidate.email.raw == "N/A"

    assert candidate.email.normalized is None

    assert candidate.email.status == "MISSING"


def test_enriched_candidate_can_require_review() -> None:
    candidate = build_candidate()

    updated = candidate.model_copy(
        update={
            "review_required": True,
            "review_reasons": [
                "INVALID_EMAIL",
                "UNRESOLVED_GEOGRAPHY",
            ],
        }
    )

    assert updated.review_required is True

    assert updated.review_reasons == [
        "INVALID_EMAIL",
        "UNRESOLVED_GEOGRAPHY",
    ]


def test_enriched_candidate_rejects_unknown_fields() -> None:
    candidate = build_candidate()

    payload = candidate.model_dump()

    payload["invented_field"] = "should fail"

    with pytest.raises(ValidationError):
        EnrichedSchoolCandidate.model_validate(payload)
