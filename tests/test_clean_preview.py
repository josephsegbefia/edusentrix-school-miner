from datetime import datetime, timezone

from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.quality.clean_preview import (
    preview_clean_crawl,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
    write_raw_page,
)


def build_preview_record(
    *,
    crawl_id: str,
    source_detail_id: str,
    page: int,
    position: int,
    name: object,
    region: object,
    phone: object,
    ownership_id: object,
) -> RawDirectoryRecord:
    return RawDirectoryRecord(
        crawl_id=crawl_id,
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=page,
        position=position,
        fetched_at=datetime(
            2026,
            8,
            18,
            15,
            0,
            tzinfo=timezone.utc,
        ),
        source_detail_id=(source_detail_id),
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": name,
            "InstitutionId": int(source_detail_id),
            "TownName": "Test Town",
            "Region": region,
            "Phone": phone,
            "OwnerShipId": ownership_id,
            "Logo": "fav.ico",
        },
    )


def test_clean_preview_summarizes_cleaning(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_preview_record(
            crawl_id=crawl_id,
            source_detail_id="1109",
            page=1,
            position=1,
            name="TEST SCHOOL ONE",
            region="Greater Accra Region",
            phone=("0302773029 or 0244826894"),
            ownership_id=2,
        ),
        build_preview_record(
            crawl_id=crawl_id,
            source_detail_id="9543",
            page=1,
            position=2,
            name="TEST SCHOOL TWO",
            region="Western Region",
            phone=None,
            ownership_id=1,
        ),
    ]

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        records,
    )

    report = preview_clean_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.raw_records_total == 2
    assert report.cleaned_records == 2
    assert report.failed_records == 0

    assert report.schools_with_phone_source == 1

    assert report.schools_without_phone_source == 1

    assert report.phone_components_total == 2

    assert report.phone_components_normalized == 2

    assert report.phone_components_unresolved == 0

    assert report.regions_normalized == 1

    assert report.regions_needing_review == 1

    assert report.regions_missing == 0

    assert report.canonical_region_counts == {
        "Greater Accra": 1,
    }

    assert report.ownership_counts == {
        "PRIVATE": 1,
        "PUBLIC": 1,
    }


def test_clean_preview_records_cleaning_failure(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    record = build_preview_record(
        crawl_id=crawl_id,
        source_detail_id="1109",
        page=1,
        position=1,
        name=None,
        region="Greater Accra Region",
        phone="0244000000",
        ownership_id=2,
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            record,
        ],
    )

    report = preview_clean_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.raw_records_total == 1
    assert report.cleaned_records == 0
    assert report.failed_records == 1

    assert len(report.failures) == 1

    assert report.failures[0].source_detail_id == "1109"

    assert report.failures[0].error_type == "ValueError"

    assert "InstitutionName" in (report.failures[0].error)
