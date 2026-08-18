from datetime import datetime, timezone
from typing import Optional

from schoolminer.models.raw import RawDirectoryRecord
from schoolminer.quality.raw_audit import (
    audit_raw_crawl,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
    write_raw_page,
)


def build_record(
    *,
    crawl_id: str,
    institution_id: int,
    page: int,
    position: int,
    region: Optional[str] = "Greater Accra Region",
    town: Optional[str] = "Accra",
    phone: Optional[str] = "0244000000",
    ownership_id: Optional[int] = 2,
) -> RawDirectoryRecord:
    source_detail_id = str(institution_id)

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
            14,
            30,
            tzinfo=timezone.utc,
        ),
        source_detail_id=(source_detail_id),
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": (f"TEST SCHOOL {institution_id}"),
            "InstitutionId": institution_id,
            "TownName": town,
            "Region": region,
            "Phone": phone,
            "OwnerShipId": ownership_id,
            "Logo": "fav.ico",
        },
    )


def test_audit_raw_crawl_counts_records(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_record(
            crawl_id=crawl_id,
            institution_id=1109,
            page=1,
            position=1,
        ),
        build_record(
            crawl_id=crawl_id,
            institution_id=9543,
            page=1,
            position=2,
        ),
    ]

    page_path = raw_page_path(
        tmp_path,
        crawl_id,
        1,
    )

    write_raw_page(
        page_path,
        records,
    )

    report = audit_raw_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.page_files == 1
    assert report.records_total == 2
    assert report.unique_source_ids == 2

    assert report.duplicate_source_ids == []

    assert report.missing_names == 0
    assert report.missing_regions == 0
    assert report.missing_towns == 0
    assert report.missing_phones == 0

    assert report.source_id_mismatches == 0

    assert report.region_counts == {
        "Greater Accra Region": 2,
    }

    assert report.ownership_counts == {
        "Public": 2,
    }


def test_audit_raw_crawl_counts_records(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_record(
            crawl_id=crawl_id,
            institution_id=1109,
            page=1,
            position=1,
        ),
        build_record(
            crawl_id=crawl_id,
            institution_id=9543,
            page=1,
            position=2,
        ),
    ]

    page_path = raw_page_path(
        tmp_path,
        crawl_id,
        1,
    )

    write_raw_page(
        page_path,
        records,
    )

    report = audit_raw_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.page_files == 1
    assert report.records_total == 2
    assert report.unique_source_ids == 2

    assert report.duplicate_source_ids == []

    assert report.missing_names == 0
    assert report.missing_regions == 0
    assert report.missing_towns == 0
    assert report.missing_phones == 0

    assert report.source_id_mismatches == 0

    assert report.region_counts == {
        "Greater Accra Region": 2,
    }

    assert report.ownership_counts == {
        "Public": 2,
    }


def test_audit_raw_crawl_counts_missing_values(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_record(
            crawl_id=crawl_id,
            institution_id=1109,
            page=1,
            position=1,
            region=None,
            town=None,
            phone=None,
            ownership_id=None,
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

    report = audit_raw_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.records_total == 1
    assert report.missing_regions == 1
    assert report.missing_towns == 1
    assert report.missing_phones == 1

    assert report.region_counts == {}

    assert report.ownership_counts == {
        "Missing": 1,
    }


def test_audit_raw_crawl_detects_duplicate_source_ids(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    first_page = [
        build_record(
            crawl_id=crawl_id,
            institution_id=1109,
            page=1,
            position=1,
        ),
    ]

    second_page = [
        build_record(
            crawl_id=crawl_id,
            institution_id=1109,
            page=2,
            position=1,
        ),
    ]

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        first_page,
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            2,
        ),
        second_page,
    )

    report = audit_raw_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.records_total == 2

    assert report.unique_source_ids == 1

    assert report.duplicate_source_ids == [
        "1109",
    ]
