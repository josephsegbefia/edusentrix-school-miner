from datetime import datetime, timezone

from schoolminer.dedupe.source_id import (
    dedupe_crawl_by_source_id,
)
from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
    write_raw_page,
)


def build_record(
    *,
    crawl_id: str,
    source_detail_id: str,
    page: int,
    position: int,
    phone: str = "0244000000",
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
            16,
            0,
            tzinfo=timezone.utc,
        ),
        source_detail_id=(source_detail_id),
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": (f"SCHOOL {source_detail_id}"),
            "InstitutionId": int(source_detail_id),
            "TownName": "Accra",
            "Region": ("Greater Accra Region"),
            "Phone": phone,
            "OwnerShipId": 2,
            "Logo": "fav.ico",
        },
    )


def test_source_id_dedupe_keeps_unique_schools(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_record(
            crawl_id=crawl_id,
            source_detail_id="1109",
            page=1,
            position=1,
        ),
        build_record(
            crawl_id=crawl_id,
            source_detail_id="9543",
            page=1,
            position=2,
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

    result = dedupe_crawl_by_source_id(
        tmp_path,
        crawl_id,
    )

    assert result.observations_total == 2
    assert result.unique_schools_total == 2

    assert result.duplicate_observations_total == 0

    assert result.duplicates == []


def test_source_id_dedupe_removes_exact_duplicate(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    first = build_record(
        crawl_id=crawl_id,
        source_detail_id="1109",
        page=1,
        position=1,
    )

    duplicate = first.model_copy(
        update={
            "page": 1,
            "position": 2,
        }
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            first,
            duplicate,
        ],
    )

    result = dedupe_crawl_by_source_id(
        tmp_path,
        crawl_id,
    )

    assert result.observations_total == 2

    assert result.unique_schools_total == 1

    assert result.duplicate_observations_total == 1

    duplicate_result = result.duplicates[0]

    assert duplicate_result.source_detail_id == "1109"

    assert duplicate_result.kept_page == 1
    assert duplicate_result.kept_position == 1

    assert duplicate_result.duplicate_page == 1

    assert duplicate_result.duplicate_position == 2

    assert duplicate_result.identical_raw_payload is True


def test_source_id_dedupe_reports_changed_duplicate_payload(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    first = build_record(
        crawl_id=crawl_id,
        source_detail_id="1109",
        page=1,
        position=1,
        phone="0244000000",
    )

    second = build_record(
        crawl_id=crawl_id,
        source_detail_id="1109",
        page=2,
        position=1,
        phone="0205000000",
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            first,
        ],
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            2,
        ),
        [
            second,
        ],
    )

    result = dedupe_crawl_by_source_id(
        tmp_path,
        crawl_id,
    )

    assert result.unique_schools_total == 1

    assert result.duplicate_observations_total == 1

    assert result.duplicates[0].identical_raw_payload is False
