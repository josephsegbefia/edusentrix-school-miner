from schoolminer.models.clean_school import (
    CleanDirectorySchool,
    CleanLocation,
    CleanPhone,
)


def test_clean_school_preserves_raw_and_normalized_values() -> None:
    school = CleanDirectorySchool(
        source="ghana_education_directory",
        source_detail_id="1109",
        name_raw="1 SIGNAL REGIMENT BASIC",
        name="1 SIGNAL REGIMENT BASIC",
        ownership_raw=2,
        ownership="PUBLIC",
        location=CleanLocation(
            region_raw="Greater Accra Region",
            region="Greater Accra",
            region_status="NORMALIZED",
            town_raw="Burma Camp, Accra",
            town="Burma Camp, Accra",
        ),
        phone_raw=("0302773029 or 0244826894"),
        phones=[
            CleanPhone(
                raw="0302773029",
                normalized="+233302773029",
            ),
            CleanPhone(
                raw="0244826894",
                normalized="+233244826894",
            ),
        ],
    )

    assert school.source_detail_id == "1109"

    assert school.location.region_raw == "Greater Accra Region"

    assert school.location.region == "Greater Accra"

    assert len(school.phones) == 2

    assert school.phones[1].normalized == "+233244826894"


def test_clean_school_allows_missing_phone() -> None:
    school = CleanDirectorySchool(
        source="ghana_education_directory",
        source_detail_id="16621",
        name_raw="TEST SCHOOL",
        name="TEST SCHOOL",
        ownership_raw=2,
        ownership="PUBLIC",
        location=CleanLocation(
            region_raw="Greater Accra Region",
            region="Greater Accra",
            region_status="NORMALIZED",
            town_raw="Accra",
            town="Accra",
        ),
        phone_raw=None,
        phones=[],
    )

    assert school.phone_raw is None
    assert school.phones == []


def test_region_can_require_review() -> None:
    location = CleanLocation(
        region_raw="Brong-Ahafo Region",
        region=None,
        region_status="NEEDS_REVIEW",
        town_raw="Test Town",
        town="Test Town",
    )

    assert location.region is None

    assert location.region_status == "NEEDS_REVIEW"
