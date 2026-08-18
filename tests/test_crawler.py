from urllib.parse import parse_qs

import httpx

from schoolminer.scraping.crawler import (
    create_directory_crawl,
    run_directory_crawl,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
)
from schoolminer.storage.sqlite_store import (
    get_crawl_job,
)


def build_api_record(
    institution_id: int,
) -> dict:
    return {
        "InstitutionName": (f"TEST SCHOOL {institution_id}"),
        "InstitutionId": institution_id,
        "TownName": "Test Town",
        "Region": "Greater Accra Region",
        "Phone": "0244000000",
        "OwnerShipId": 2,
        "Logo": "fav.ico",
    }


def build_transport() -> httpx.MockTransport:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                request=request,
                text="""
                <html>
                    <body>
                        <input
                            name="__RequestVerificationToken"
                            value="test-token"
                        />
                    </body>
                </html>
                """,
            )

        form_data = parse_qs(
            request.content.decode("utf-8"),
            keep_blank_values=True,
        )

        page = int(form_data["Spara[page]"][0])

        first_id = page * 100

        records = [
            build_api_record(first_id + offset)
            for offset in range(
                1,
                6,
            )
        ]

        return httpx.Response(
            200,
            request=request,
            json={
                "Data": records,
                "PageCount": 100,
            },
        )

    return httpx.MockTransport(handler)


def test_create_directory_crawl_persists_job(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = create_directory_crawl(
        database_path,
        region_filter="All",
    )

    loaded_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    assert loaded_job is not None

    assert loaded_job.status == "PENDING"

    assert loaded_job.next_page == 1

    assert loaded_job.records_saved == 0

    assert loaded_job.category == "Junior High School"


def test_run_directory_crawl_acquires_ten_records(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    transport = build_transport()

    with httpx.Client(transport=transport) as client:
        final_job = run_directory_crawl(
            client,
            state_db_path=database_path,
            raw_dir=raw_dir,
            crawl_id=job.crawl_id,
            limit=10,
            delay_seconds=0,
        )

    assert final_job.status == "PAUSED"

    assert final_job.total_pages == 100

    assert final_job.next_page == 3

    assert final_job.records_saved == 10

    page_one = raw_page_path(
        raw_dir,
        job.crawl_id,
        1,
    )

    page_two = raw_page_path(
        raw_dir,
        job.crawl_id,
        2,
    )

    assert page_one.exists()
    assert page_two.exists()

    assert len(page_one.read_text(encoding="utf-8").splitlines()) == 5

    assert len(page_two.read_text(encoding="utf-8").splitlines()) == 5


def test_directory_crawl_resumes_from_checkpoint(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    raw_dir = tmp_path / "raw"

    job = create_directory_crawl(
        database_path,
    )

    transport = build_transport()

    with httpx.Client(transport=transport) as client:
        first_run = run_directory_crawl(
            client,
            state_db_path=database_path,
            raw_dir=raw_dir,
            crawl_id=job.crawl_id,
            limit=10,
            delay_seconds=0,
        )

        assert first_run.next_page == 3

        second_run = run_directory_crawl(
            client,
            state_db_path=database_path,
            raw_dir=raw_dir,
            crawl_id=job.crawl_id,
            limit=5,
            delay_seconds=0,
        )

    assert second_run.status == "PAUSED"

    assert second_run.next_page == 4

    assert second_run.records_saved == 15

    page_three = raw_page_path(
        raw_dir,
        job.crawl_id,
        3,
    )

    assert page_three.exists()
