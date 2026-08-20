from datetime import datetime, timezone

import httpx
import pytest

from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.scraping.crawler import (
    create_directory_crawl,
)
from schoolminer.scraping.detail_crawler import (
    run_detail_acquisition,
    unique_source_detail_ids,
)
from schoolminer.storage.raw_store import (
    raw_detail_path,
    raw_page_path,
    write_raw_page,
)
from schoolminer.storage.sqlite_store import (
    get_detail_fetch,
)


def build_listing_record(
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
            20,
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
            "TownName": "Test Town",
            "Region": ("Greater Accra Region"),
            "Phone": "0244000000",
            "OwnerShipId": 2,
            "Logo": "fav.ico",
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
                        999
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
                            <strong>District :</strong>
                        </td>

                        <td>
                            Test District
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """


def seed_listing_records(
    raw_dir,
    crawl_id: str,
    source_ids: list[str],
) -> None:
    records = [
        build_listing_record(
            crawl_id=crawl_id,
            source_detail_id=source_id,
            page=1,
            position=index,
        )
        for index, source_id in enumerate(
            source_ids,
            start=1,
        )
    ]

    write_raw_page(
        raw_page_path(
            raw_dir,
            crawl_id,
            1,
        ),
        records,
    )


def test_detail_acquisition_fetches_unique_ids_only(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    seed_listing_records(
        raw_dir,
        job.crawl_id,
        [
            "1109",
            "1109",
            "9543",
        ],
    )

    requested_ids = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        source_id = request.url.path.rstrip("/").split("/")[-1]

        requested_ids.append(source_id)

        return httpx.Response(
            200,
            request=request,
            text=build_detail_html(source_id),
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        result = run_detail_acquisition(
            client,
            state_db_path=(database_path),
            raw_dir=raw_dir,
            crawl_id=job.crawl_id,
            limit=10,
            delay_seconds=0,
        )

    assert requested_ids == [
        "1109",
        "9543",
    ]

    assert result.candidates_total == 2

    assert result.completed_this_run == 2

    assert result.completed_total == 2
    assert result.remaining_total == 0

    assert raw_detail_path(
        raw_dir,
        job.crawl_id,
        "1109",
    ).exists()

    assert raw_detail_path(
        raw_dir,
        job.crawl_id,
        "9543",
    ).exists()


def test_detail_acquisition_resumes_completed_ids(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    seed_listing_records(
        raw_dir,
        job.crawl_id,
        [
            "1109",
            "9543",
            "9730",
        ],
    )

    requested_ids = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        source_id = request.url.path.rstrip("/").split("/")[-1]

        requested_ids.append(source_id)

        return httpx.Response(
            200,
            request=request,
            text=build_detail_html(source_id),
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        first_run = run_detail_acquisition(
            client,
            state_db_path=(database_path),
            raw_dir=raw_dir,
            crawl_id=(job.crawl_id),
            limit=1,
            delay_seconds=0,
        )

        second_run = run_detail_acquisition(
            client,
            state_db_path=(database_path),
            raw_dir=raw_dir,
            crawl_id=(job.crawl_id),
            limit=1,
            delay_seconds=0,
        )

    assert first_run.completed_total == 1

    assert second_run.completed_total == 2

    assert requested_ids == [
        "1109",
        "9543",
    ]


def test_detail_acquisition_retries_temporary_failure(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    seed_listing_records(
        raw_dir,
        job.crawl_id,
        [
            "1109",
        ],
    )

    attempts = 0
    sleep_calls = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal attempts

        attempts += 1

        if attempts == 1:
            return httpx.Response(
                503,
                request=request,
            )

        return httpx.Response(
            200,
            request=request,
            text=build_detail_html("1109"),
        )

    monkeypatch.setattr(
        "schoolminer.scraping.detail_crawler.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        result = run_detail_acquisition(
            client,
            state_db_path=(database_path),
            raw_dir=raw_dir,
            crawl_id=job.crawl_id,
            limit=1,
            delay_seconds=0,
            max_attempts=3,
            retry_base_delay_seconds=2,
        )

    checkpoint = get_detail_fetch(
        database_path,
        job.crawl_id,
        "1109",
    )

    assert checkpoint is not None

    assert attempts == 2
    assert sleep_calls == [2]

    assert checkpoint.attempts == 2

    assert checkpoint.status == "COMPLETED"

    assert result.completed_total == 1


def test_detail_acquisition_rejects_non_school_html(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    seed_listing_records(
        raw_dir,
        job.crawl_id,
        [
            "1109",
        ],
    )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            text=("<html><body>Something unexpected</body></html>"),
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(
            ValueError,
            match="school name",
        ):
            run_detail_acquisition(
                client,
                state_db_path=(database_path),
                raw_dir=raw_dir,
                crawl_id=(job.crawl_id),
                limit=1,
                delay_seconds=0,
            )

    checkpoint = get_detail_fetch(
        database_path,
        job.crawl_id,
        "1109",
    )

    assert checkpoint is not None

    assert checkpoint.status == "FAILED"

    assert raw_detail_path(
        raw_dir,
        job.crawl_id,
        "1109",
    ).exists()
