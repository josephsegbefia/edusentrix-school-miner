from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from schoolminer.models.crawl import CrawlJob


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
