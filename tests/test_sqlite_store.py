import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from schoolminer.models.crawl import CrawlJob
from schoolminer.storage.sqlite_store import (
    complete_crawl_page,
    create_crawl_job,
    fail_crawl_page,
    get_crawl_job,
    get_crawl_page,
    initialize_database,
    set_crawl_total_pages,
    start_crawl_page,
    update_crawl_status,
)


def build_crawl_job() -> CrawlJob:
    timestamp = datetime(
        2026,
        8,
        18,
        1,
        45,
        tzinfo=timezone.utc,
    )

    return CrawlJob(
        crawl_id="jhs-test-abc123",
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        status="PENDING",
        created_at=timestamp,
        updated_at=timestamp,
        total_pages=None,
        next_page=1,
        records_saved=0,
        last_error=None,
    )


def test_initialize_database_creates_state_tables(
    tmp_path,
) -> None:
    database_path = tmp_path / "state" / "schoolminer.sqlite3"

    initialize_database(database_path)

    assert database_path.exists()

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    finally:
        connection.close()

    table_names = {row[0] for row in rows}

    assert "crawl_jobs" in table_names
    assert "crawl_pages" in table_names


def test_create_and_get_crawl_job(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    loaded_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    assert loaded_job is not None

    assert loaded_job.crawl_id == "jhs-test-abc123"

    assert loaded_job.category == "Junior High School"

    assert loaded_job.status == "PENDING"

    assert loaded_job.next_page == 1
    assert loaded_job.records_saved == 0

    assert loaded_job.created_at == job.created_at


def test_get_crawl_job_returns_none_when_missing(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    initialize_database(database_path)

    loaded_job = get_crawl_job(
        database_path,
        "does-not-exist",
    )

    assert loaded_job is None


def test_duplicate_crawl_id_is_rejected(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_crawl_job(
            database_path,
            job,
        )


def test_update_crawl_status_and_total_pages(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    later = job.updated_at + timedelta(minutes=1)

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        later,
    )

    set_crawl_total_pages(
        database_path,
        job.crawl_id,
        1730,
        later,
    )

    loaded_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    assert loaded_job is not None
    assert loaded_job.status == "RUNNING"
    assert loaded_job.total_pages == 1730


def test_start_crawl_page_tracks_attempts(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        job.updated_at,
    )

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        job.updated_at,
    )

    first_attempt = get_crawl_page(
        database_path,
        job.crawl_id,
        1,
    )

    assert first_attempt is not None
    assert first_attempt.status == "IN_PROGRESS"
    assert first_attempt.attempts == 1

    retry_time = job.updated_at + timedelta(minutes=1)

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        retry_time,
    )

    second_attempt = get_crawl_page(
        database_path,
        job.crawl_id,
        1,
    )

    assert second_attempt is not None
    assert second_attempt.attempts == 2


def test_complete_crawl_page_advances_checkpoint(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        job.updated_at,
    )

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        job.updated_at,
    )

    completed_at = job.updated_at + timedelta(minutes=1)

    complete_crawl_page(
        database_path,
        job.crawl_id,
        1,
        5,
        completed_at,
    )

    loaded_page = get_crawl_page(
        database_path,
        job.crawl_id,
        1,
    )

    loaded_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    assert loaded_page is not None
    assert loaded_job is not None

    assert loaded_page.status == "COMPLETED"
    assert loaded_page.records_saved == 5

    assert loaded_job.next_page == 2
    assert loaded_job.records_saved == 5


def test_failed_page_can_be_resumed(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        job.updated_at,
    )

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        job.updated_at,
    )

    failed_at = job.updated_at + timedelta(minutes=1)

    fail_crawl_page(
        database_path,
        job.crawl_id,
        1,
        "HTTP 500",
        failed_at,
    )

    failed_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    failed_page = get_crawl_page(
        database_path,
        job.crawl_id,
        1,
    )

    assert failed_job is not None
    assert failed_page is not None

    assert failed_job.status == "FAILED"

    assert failed_job.next_page == 1

    assert failed_page.status == "FAILED"

    resume_time = failed_at + timedelta(minutes=1)

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        resume_time,
    )

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        resume_time,
    )

    retried_page = get_crawl_page(
        database_path,
        job.crawl_id,
        1,
    )

    assert retried_page is not None

    assert retried_page.status == "IN_PROGRESS"

    assert retried_page.attempts == 2


def test_crawl_cannot_start_page_out_of_order(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        job.updated_at,
    )

    with pytest.raises(
        ValueError,
        match="next page is 1",
    ):
        start_crawl_page(
            database_path,
            job.crawl_id,
            2,
            job.updated_at,
        )


def test_completed_page_cannot_be_counted_twice(
    tmp_path,
) -> None:
    database_path = tmp_path / "schoolminer.sqlite3"

    job = build_crawl_job()

    create_crawl_job(
        database_path,
        job,
    )

    update_crawl_status(
        database_path,
        job.crawl_id,
        "RUNNING",
        job.updated_at,
    )

    start_crawl_page(
        database_path,
        job.crawl_id,
        1,
        job.updated_at,
    )

    complete_crawl_page(
        database_path,
        job.crawl_id,
        1,
        5,
        job.updated_at,
    )

    with pytest.raises(
        ValueError,
        match="not currently in progress",
    ):
        complete_crawl_page(
            database_path,
            job.crawl_id,
            1,
            5,
            job.updated_at,
        )

    loaded_job = get_crawl_job(
        database_path,
        job.crawl_id,
    )

    assert loaded_job is not None

    assert loaded_job.records_saved == 5
