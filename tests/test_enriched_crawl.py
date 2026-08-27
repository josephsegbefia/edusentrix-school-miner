from datetime import datetime, timezone

import pytest

from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.processing.enriched_crawl import (
    build_enriched_crawl,
)
from schoolminer.storage.raw_store import (
    raw_detail_path,
    raw_page_path,
    write_raw_page,
    write_raw_text,
)


def build_listing(
    *,
    crawl_id: str,
    source_detail_id: str,
    position: int,
) -> RawDirectoryRecord:
    return RawDirectoryRecord(
        crawl_id=crawl_id,
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=1,
        position=position,
        fetched_at=datetime(
            2026,
            8,
            27,
            12,
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
            "Logo": None,
        },
    )


def build_detail_html(
    source_detail_id: str,
) -> str:
    return f"""
    <html>
        <body>
            <div>
                <h4 class="detail_title">
                    <span class="label label-danger">
                        100
                    </span>

                    <b>
                        SCHOOL {source_detail_id}
                    </b>
                </h4>

                <span class="label label-success">
                    Public
                </span>

                <span class="label label-success mixl">
                    Mixed
                </span>

                <span class="label label-success levls">
                    Junior High School
                </span>

                <span class="label label-success regl">
                    Greater Accra Region
                </span>

                <table class="table table-user-information">
                    <tr>
                        <td>
                            <strong>Phone :</strong>
                        </td>
                        <td>
                            0244000000
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Email :</strong>
                        </td>
                        <td>
                            N/A
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>District :</strong>
                        </td>
                        <td>
                            Accra Metro
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """


def test_build_enriched_crawl_builds_candidates(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    records = [
        build_listing(
            crawl_id=crawl_id,
            source_detail_id="1109",
            position=1,
        ),
        build_listing(
            crawl_id=crawl_id,
            source_detail_id="9543",
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

    for source_id in [
        "1109",
        "9543",
    ]:
        write_raw_text(
            raw_detail_path(
                tmp_path,
                crawl_id,
                source_id,
            ),
            build_detail_html(source_id),
        )

    candidates = build_enriched_crawl(
        tmp_path,
        crawl_id,
    )

    assert len(candidates) == 2

    assert [candidate.source_detail_id for candidate in candidates] == [
        "1109",
        "9543",
    ]

    assert all(candidate.location.canonical_region == "Greater Accra" for candidate in candidates)


def test_build_enriched_crawl_deduplicates_source_ids(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    first = build_listing(
        crawl_id=crawl_id,
        source_detail_id="1109",
        position=1,
    )

    duplicate = first.model_copy(
        update={
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

    write_raw_text(
        raw_detail_path(
            tmp_path,
            crawl_id,
            "1109",
        ),
        build_detail_html("1109"),
    )

    candidates = build_enriched_crawl(
        tmp_path,
        crawl_id,
    )

    assert len(candidates) == 1

    assert candidates[0].source_detail_id == "1109"


def test_build_enriched_crawl_requires_detail_page(
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
            build_listing(
                crawl_id=crawl_id,
                source_detail_id="1109",
                position=1,
            ),
        ],
    )

    with pytest.raises(
        FileNotFoundError,
        match="1109",
    ):
        build_enriched_crawl(
            tmp_path,
            crawl_id,
        )
