from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from schoolminer.models.crawl import (
    CrawlJob,
    CrawlPage,
    CrawlStatus,
    DetailFetch,
)


def _connect(
    path: Path,
) -> sqlite3.Connection:
    """Open the local School Miner state database."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(path)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database(
    path: Path,
) -> None:
    """Create the School Miner state database schema."""

    connection = _connect(path)

    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS crawl_jobs (
                crawl_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                region_filter TEXT NOT NULL,

                status TEXT NOT NULL
                    CHECK (
                        status IN (
                            'PENDING',
                            'RUNNING',
                            'PAUSED',
                            'COMPLETED',
                            'FAILED'
                        )
                    ),

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                total_pages INTEGER
                    CHECK (
                        total_pages IS NULL
                        OR total_pages >= 1
                    ),

                next_page INTEGER NOT NULL DEFAULT 1
                    CHECK (next_page >= 1),

                records_saved INTEGER NOT NULL DEFAULT 0
                    CHECK (records_saved >= 0),

                last_error TEXT
            );


            CREATE TABLE IF NOT EXISTS crawl_pages (
                crawl_id TEXT NOT NULL,
                page_number INTEGER NOT NULL
                    CHECK (page_number >= 1),

                status TEXT NOT NULL
                    CHECK (
                        status IN (
                            'PENDING',
                            'IN_PROGRESS',
                            'COMPLETED',
                            'FAILED'
                        )
                    ),

                attempts INTEGER NOT NULL DEFAULT 0
                    CHECK (attempts >= 0),

                records_saved INTEGER NOT NULL DEFAULT 0
                    CHECK (records_saved >= 0),

                started_at TEXT,
                completed_at TEXT,
                last_error TEXT,

                PRIMARY KEY (
                    crawl_id,
                    page_number
                ),

                FOREIGN KEY (
                    crawl_id
                )
                REFERENCES crawl_jobs (
                    crawl_id
                )
                ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS detail_fetches (
                crawl_id TEXT NOT NULL,
                source_detail_id TEXT NOT NULL,

                status TEXT NOT NULL
                    CHECK (
                        status IN (
                            'IN_PROGRESS',
                            'COMPLETED',
                            'FAILED'
                        )
                    ),

                attempts INTEGER NOT NULL DEFAULT 0
                    CHECK (attempts >= 0),

                started_at TEXT,
                completed_at TEXT,

                http_status INTEGER,
                content_length INTEGER
                    CHECK (
                        content_length IS NULL
                        OR content_length >= 0
                    ),

                last_error TEXT,

                PRIMARY KEY (
                    crawl_id,
                    source_detail_id
                ),

                FOREIGN KEY (
                    crawl_id
                )
                REFERENCES crawl_jobs (
                    crawl_id
                )
                ON DELETE CASCADE
            );
            """
        )

        connection.commit()

    finally:
        connection.close()


def create_crawl_job(
    path: Path,
    job: CrawlJob,
) -> None:
    """Persist a new crawl job."""

    initialize_database(path)

    connection = _connect(path)

    try:
        connection.execute(
            """
            INSERT INTO crawl_jobs (
                crawl_id,
                source,
                category,
                region_filter,
                status,
                created_at,
                updated_at,
                total_pages,
                next_page,
                records_saved,
                last_error
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                job.crawl_id,
                job.source,
                job.category,
                job.region_filter,
                job.status,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.total_pages,
                job.next_page,
                job.records_saved,
                job.last_error,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def get_crawl_job(
    path: Path,
    crawl_id: str,
) -> Optional[CrawlJob]:
    """Load one crawl job from the state database."""

    initialize_database(path)

    connection = _connect(path)

    try:
        row = connection.execute(
            """
            SELECT
                crawl_id,
                source,
                category,
                region_filter,
                status,
                created_at,
                updated_at,
                total_pages,
                next_page,
                records_saved,
                last_error
            FROM crawl_jobs
            WHERE crawl_id = ?
            """,
            (crawl_id,),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return CrawlJob.model_validate(dict(row))


def update_crawl_status(
    path: Path,
    crawl_id: str,
    status: CrawlStatus,
    updated_at: datetime,
    *,
    last_error: Optional[str] = None,
) -> None:
    """Update the lifecycle status of an existing crawl."""

    initialize_database(path)

    connection = _connect(path)

    try:
        cursor = connection.execute(
            """
            UPDATE crawl_jobs
            SET
                status = ?,
                updated_at = ?,
                last_error = ?
            WHERE crawl_id = ?
            """,
            (
                status,
                updated_at.isoformat(),
                last_error,
                crawl_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(f"Crawl job does not exist: {crawl_id}")

        connection.commit()

    finally:
        connection.close()


def set_crawl_total_pages(
    path: Path,
    crawl_id: str,
    total_pages: int,
    updated_at: datetime,
) -> None:
    """Store the source-reported page count for a crawl."""

    if total_pages < 1:
        raise ValueError("total_pages must be at least 1.")

    initialize_database(path)

    connection = _connect(path)

    try:
        cursor = connection.execute(
            """
            UPDATE crawl_jobs
            SET
                total_pages = ?,
                updated_at = ?
            WHERE crawl_id = ?
            """,
            (
                total_pages,
                updated_at.isoformat(),
                crawl_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(f"Crawl job does not exist: {crawl_id}")

        connection.commit()

    finally:
        connection.close()


def get_crawl_page(
    path: Path,
    crawl_id: str,
    page_number: int,
) -> Optional[CrawlPage]:
    """Load one page checkpoint from the state database."""

    initialize_database(path)

    connection = _connect(path)

    try:
        row = connection.execute(
            """
            SELECT
                crawl_id,
                page_number,
                status,
                attempts,
                records_saved,
                started_at,
                completed_at,
                last_error
            FROM crawl_pages
            WHERE
                crawl_id = ?
                AND page_number = ?
            """,
            (
                crawl_id,
                page_number,
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return CrawlPage.model_validate(dict(row))


def start_crawl_page(
    path: Path,
    crawl_id: str,
    page_number: int,
    started_at: datetime,
) -> None:
    """Mark the crawl's next page as in progress."""

    initialize_database(path)

    connection = _connect(path)

    try:
        job = connection.execute(
            """
            SELECT
                status,
                next_page
            FROM crawl_jobs
            WHERE crawl_id = ?
            """,
            (crawl_id,),
        ).fetchone()

        if job is None:
            raise ValueError(f"Crawl job does not exist: {crawl_id}")

        if job["status"] != "RUNNING":
            raise ValueError("A page can only start while the crawl is RUNNING.")

        if job["next_page"] != page_number:
            raise ValueError(f"Cannot start page {page_number}; next page is {job['next_page']}.")

        existing_page = connection.execute(
            """
            SELECT
                status,
                attempts
            FROM crawl_pages
            WHERE
                crawl_id = ?
                AND page_number = ?
            """,
            (
                crawl_id,
                page_number,
            ),
        ).fetchone()

        if existing_page is None:
            connection.execute(
                """
                INSERT INTO crawl_pages (
                    crawl_id,
                    page_number,
                    status,
                    attempts,
                    records_saved,
                    started_at,
                    completed_at,
                    last_error
                )
                VALUES (
                    ?,
                    ?,
                    'IN_PROGRESS',
                    1,
                    0,
                    ?,
                    NULL,
                    NULL
                )
                """,
                (
                    crawl_id,
                    page_number,
                    started_at.isoformat(),
                ),
            )

        else:
            if existing_page["status"] == "COMPLETED":
                raise ValueError(f"Page {page_number} is already completed.")

            connection.execute(
                """
                UPDATE crawl_pages
                SET
                    status = 'IN_PROGRESS',
                    attempts = attempts + 1,
                    started_at = ?,
                    completed_at = NULL,
                    last_error = NULL
                WHERE
                    crawl_id = ?
                    AND page_number = ?
                """,
                (
                    started_at.isoformat(),
                    crawl_id,
                    page_number,
                ),
            )

        connection.execute(
            """
            UPDATE crawl_jobs
            SET
                updated_at = ?,
                last_error = NULL
            WHERE crawl_id = ?
            """,
            (
                started_at.isoformat(),
                crawl_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def complete_crawl_page(
    path: Path,
    crawl_id: str,
    page_number: int,
    records_saved: int,
    completed_at: datetime,
) -> None:
    """Complete a page and atomically advance the crawl."""

    if records_saved < 0:
        raise ValueError("records_saved cannot be negative.")

    initialize_database(path)

    connection = _connect(path)

    try:
        page = connection.execute(
            """
            SELECT status
            FROM crawl_pages
            WHERE
                crawl_id = ?
                AND page_number = ?
            """,
            (
                crawl_id,
                page_number,
            ),
        ).fetchone()

        if page is None:
            raise ValueError(f"Page {page_number} has not been started.")

        if page["status"] != "IN_PROGRESS":
            raise ValueError(f"Page {page_number} is not currently in progress.")

        connection.execute(
            """
            UPDATE crawl_pages
            SET
                status = 'COMPLETED',
                records_saved = ?,
                completed_at = ?,
                last_error = NULL
            WHERE
                crawl_id = ?
                AND page_number = ?
            """,
            (
                records_saved,
                completed_at.isoformat(),
                crawl_id,
                page_number,
            ),
        )

        cursor = connection.execute(
            """
            UPDATE crawl_jobs
            SET
                next_page = next_page + 1,
                records_saved = (
                    records_saved + ?
                ),
                updated_at = ?,
                last_error = NULL
            WHERE
                crawl_id = ?
                AND next_page = ?
            """,
            (
                records_saved,
                completed_at.isoformat(),
                crawl_id,
                page_number,
            ),
        )

        if cursor.rowcount != 1:
            connection.rollback()

            raise ValueError("Crawl checkpoint no longer matches the page being completed.")

        connection.commit()

    finally:
        connection.close()


def fail_crawl_page(
    path: Path,
    crawl_id: str,
    page_number: int,
    error: str,
    failed_at: datetime,
) -> None:
    """Record a page failure without advancing the crawl."""

    initialize_database(path)

    connection = _connect(path)

    try:
        cursor = connection.execute(
            """
            UPDATE crawl_pages
            SET
                status = 'FAILED',
                last_error = ?
            WHERE
                crawl_id = ?
                AND page_number = ?
            """,
            (
                error,
                crawl_id,
                page_number,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(f"Page {page_number} has not been started.")

        connection.execute(
            """
            UPDATE crawl_jobs
            SET
                status = 'FAILED',
                updated_at = ?,
                last_error = ?
            WHERE crawl_id = ?
            """,
            (
                failed_at.isoformat(),
                error,
                crawl_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def get_detail_fetch(
    path: Path,
    crawl_id: str,
    source_detail_id: str,
) -> Optional[DetailFetch]:
    """Load one detail-page acquisition checkpoint."""

    initialize_database(path)

    connection = _connect(path)

    try:
        row = connection.execute(
            """
            SELECT
                crawl_id,
                source_detail_id,
                status,
                attempts,
                started_at,
                completed_at,
                http_status,
                content_length,
                last_error
            FROM detail_fetches
            WHERE
                crawl_id = ?
                AND source_detail_id = ?
            """,
            (
                crawl_id,
                source_detail_id,
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return DetailFetch.model_validate(dict(row))


def start_detail_fetch(
    path: Path,
    crawl_id: str,
    source_detail_id: str,
    started_at: datetime,
) -> None:
    """Start or retry one school detail-page acquisition."""

    initialize_database(path)

    connection = _connect(path)

    try:
        crawl = connection.execute(
            """
            SELECT crawl_id
            FROM crawl_jobs
            WHERE crawl_id = ?
            """,
            (crawl_id,),
        ).fetchone()

        if crawl is None:
            raise ValueError(f"Crawl job does not exist: {crawl_id}")

        existing = connection.execute(
            """
            SELECT
                status,
                attempts
            FROM detail_fetches
            WHERE
                crawl_id = ?
                AND source_detail_id = ?
            """,
            (
                crawl_id,
                source_detail_id,
            ),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO detail_fetches (
                    crawl_id,
                    source_detail_id,
                    status,
                    attempts,
                    started_at,
                    completed_at,
                    http_status,
                    content_length,
                    last_error
                )
                VALUES (
                    ?,
                    ?,
                    'IN_PROGRESS',
                    1,
                    ?,
                    NULL,
                    NULL,
                    NULL,
                    NULL
                )
                """,
                (
                    crawl_id,
                    source_detail_id,
                    started_at.isoformat(),
                ),
            )

        else:
            if existing["status"] == "COMPLETED":
                raise ValueError(
                    f"Detail page is already completed for source ID {source_detail_id}."
                )

            connection.execute(
                """
                UPDATE detail_fetches
                SET
                    status = 'IN_PROGRESS',
                    attempts = attempts + 1,
                    started_at = ?,
                    completed_at = NULL,
                    http_status = NULL,
                    content_length = NULL,
                    last_error = NULL
                WHERE
                    crawl_id = ?
                    AND source_detail_id = ?
                """,
                (
                    started_at.isoformat(),
                    crawl_id,
                    source_detail_id,
                ),
            )

        connection.commit()

    finally:
        connection.close()


def complete_detail_fetch(
    path: Path,
    crawl_id: str,
    source_detail_id: str,
    *,
    http_status: int,
    content_length: int,
    completed_at: datetime,
) -> None:
    """Mark one persisted detail page as completed."""

    if content_length < 0:
        raise ValueError("content_length cannot be negative.")

    initialize_database(path)

    connection = _connect(path)

    try:
        cursor = connection.execute(
            """
            UPDATE detail_fetches
            SET
                status = 'COMPLETED',
                completed_at = ?,
                http_status = ?,
                content_length = ?,
                last_error = NULL
            WHERE
                crawl_id = ?
                AND source_detail_id = ?
                AND status = 'IN_PROGRESS'
            """,
            (
                completed_at.isoformat(),
                http_status,
                content_length,
                crawl_id,
                source_detail_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                f"Detail fetch is not currently in progress for source ID {source_detail_id}."
            )

        connection.commit()

    finally:
        connection.close()


def fail_detail_fetch(
    path: Path,
    crawl_id: str,
    source_detail_id: str,
    error: str,
) -> None:
    """Mark one detail-page acquisition as failed."""

    initialize_database(path)

    connection = _connect(path)

    try:
        cursor = connection.execute(
            """
            UPDATE detail_fetches
            SET
                status = 'FAILED',
                last_error = ?
            WHERE
                crawl_id = ?
                AND source_detail_id = ?
            """,
            (
                error,
                crawl_id,
                source_detail_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(f"Detail fetch has not been started for source ID {source_detail_id}.")

        connection.commit()

    finally:
        connection.close()
