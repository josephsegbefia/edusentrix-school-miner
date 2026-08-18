import sqlite3
from datetime import datetime, timezone

import pytest

from schoolminer.models.crawl import CrawlJob
from schoolminer.storage.sqlite_store import (
    create_crawl_job,
    get_crawl_job,
    initialize_database,
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
