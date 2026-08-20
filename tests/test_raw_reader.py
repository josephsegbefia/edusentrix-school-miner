from datetime import datetime, timezone

import pytest

from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.storage.raw_reader import (
    iter_raw_crawl_records,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
    write_raw_page,
)


def build_raw_record(
    *,
    crawl_id: str,
    source_detail_id: str,
    page: int,
    position: int,
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
            "InstitutionName": (f"SCHOOL {source_detail_id}"),
            "InstitutionId": int(source_detail_id),
            "TownName": "Accra",
            "Region": ("Greater Accra Region"),
            "Phone": "0244000000",
            "OwnerShipId": 2,
            "Logo": "fav.ico",
        },
    )


def test_raw_reader_reads_pages_in_order(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            build_raw_record(
                crawl_id=crawl_id,
                source_detail_id="1109",
                page=1,
                position=1,
            )
        ],
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            2,
        ),
        [
            build_raw_record(
                crawl_id=crawl_id,
                source_detail_id="9543",
                page=2,
                position=1,
            )
        ],
    )

    records = list(
        iter_raw_crawl_records(
            tmp_path,
            crawl_id,
        )
    )

    assert len(records) == 2

    assert records[0].source_detail_id == "1109"

    assert records[1].source_detail_id == "9543"


def test_raw_reader_rejects_invalid_json(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    page_path = raw_page_path(
        tmp_path,
        crawl_id,
        1,
    )

    page_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_path.write_text(
        '{"broken":\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        list(
            iter_raw_crawl_records(
                tmp_path,
                crawl_id,
            )
        )
