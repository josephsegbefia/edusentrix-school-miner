from datetime import datetime, timezone

from schoolminer.cleaning.locations import (
    normalize_region,
)
from schoolminer.cleaning.ownership import (
    normalize_ownership,
)
from schoolminer.cleaning.phones import (
    clean_phone_field,
    normalize_ghana_phone,
)
from schoolminer.cleaning.schools import (
    clean_directory_school,
)
from schoolminer.cleaning.text import (
    clean_text,
)
from schoolminer.models.raw import (
    RawDirectoryRecord,
)


def test_clean_text_collapses_whitespace() -> None:
    assert clean_text("  A. M. E.   ZION  ") == "A. M. E. ZION"


def test_normalize_ghana_phone_handles_local_number() -> None:
    assert normalize_ghana_phone("0244 123 456") == "+233244123456"


def test_normalize_ghana_phone_handles_country_code() -> None:
    assert normalize_ghana_phone("+233244123456") == "+233244123456"


def test_normalize_ghana_phone_does_not_guess_invalid_number() -> None:
    assert normalize_ghana_phone("12345") is None


def test_clean_phone_field_splits_multiple_numbers() -> None:
    phones = clean_phone_field("0302773029 or 0244826894")

    assert len(phones) == 2

    assert phones[0].raw == "0302773029"

    assert phones[0].normalized == "+233302773029"

    assert phones[1].raw == "0244826894"

    assert phones[1].normalized == "+233244826894"


def test_ownership_mapping() -> None:
    assert normalize_ownership(1) == "PRIVATE"

    assert normalize_ownership(2) == "PUBLIC"

    assert normalize_ownership(99) == "UNKNOWN"


def test_unambiguous_region_is_normalized() -> None:
    region, status = normalize_region("Greater Accra Region")

    assert region == "Greater Accra"
    assert status == "NORMALIZED"


def test_historical_region_requires_review() -> None:
    region, status = normalize_region("Western Region")

    assert region is None
    assert status == "NEEDS_REVIEW"


def test_clean_directory_school_transforms_raw_record() -> None:
    raw_record = RawDirectoryRecord(
        crawl_id="test-crawl",
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=1,
        position=1,
        fetched_at=datetime(
            2026,
            8,
            18,
            13,
            10,
            tzinfo=timezone.utc,
        ),
        source_detail_id="1109",
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=("https://ghanaeducationdirectory.com/Search/Details/1109"),
        raw={
            "InstitutionName": ("  1 SIGNAL   REGIMENT BASIC "),
            "InstitutionId": 1109,
            "TownName": "Burma Camp, Accra",
            "Region": ("Greater Accra Region"),
            "Phone": ("0302773029 or 0244826894"),
            "OwnerShipId": 2,
            "Logo": "test.png",
        },
    )

    school = clean_directory_school(raw_record)

    assert school.source_detail_id == "1109"

    assert school.name_raw == "  1 SIGNAL   REGIMENT BASIC "

    assert school.name == "1 SIGNAL REGIMENT BASIC"

    assert school.ownership == "PUBLIC"

    assert school.location.region_raw == "Greater Accra Region"

    assert school.location.region == "Greater Accra"

    assert school.location.region_status == "NORMALIZED"

    assert school.location.town == "Burma Camp, Accra"

    assert len(school.phones) == 2

    assert school.phones[0].normalized == "+233302773029"

    assert school.phones[1].normalized == "+233244826894"
