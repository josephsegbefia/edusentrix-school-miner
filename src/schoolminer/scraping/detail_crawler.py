from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import httpx

from schoolminer.config import (
    DEFAULT_MAX_PAGE_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY_SECONDS,
)
from schoolminer.models.detail_acquisition import (
    DetailAcquisitionResult,
)
from schoolminer.scraping.crawler import (
    utc_now,
)
from schoolminer.scraping.retry import (
    is_retryable_http_error,
    retry_delay,
)
from schoolminer.sources.ghana_education_directory import (
    fetch_detail_page,
    parse_detail_page,
)
from schoolminer.storage.raw_reader import (
    iter_raw_crawl_records,
)
from schoolminer.storage.raw_store import (
    raw_detail_path,
    write_raw_text,
)
from schoolminer.storage.sqlite_store import (
    complete_detail_fetch,
    fail_detail_fetch,
    get_crawl_job,
    get_detail_fetch,
    start_detail_fetch,
)


DetailCompletedCallback = Callable[
    [str, int, int],
    None,
]


DetailRetryCallback = Callable[
    [str, int, int, float, str],
    None,
]


def unique_source_detail_ids(
    raw_dir: Path,
    crawl_id: str,
) -> list[str]:
    """Return unique source detail IDs in first-seen order."""

    seen = set()
    source_ids = []

    for record in iter_raw_crawl_records(
        raw_dir,
        crawl_id,
    ):
        source_id = record.source_detail_id

        if source_id in seen:
            continue

        seen.add(source_id)

        source_ids.append(source_id)

    return source_ids


def _count_completed_details(
    state_db_path: Path,
    crawl_id: str,
    source_ids: list[str],
) -> int:
    """Count completed detail checkpoints for candidate IDs."""

    completed = 0

    for source_id in source_ids:
        checkpoint = get_detail_fetch(
            state_db_path,
            crawl_id,
            source_id,
        )

        if checkpoint is not None and checkpoint.status == "COMPLETED":
            completed += 1

    return completed


def run_detail_acquisition(
    client: httpx.Client,
    *,
    state_db_path: Path,
    raw_dir: Path,
    crawl_id: str,
    limit: int,
    delay_seconds: float = 1.0,
    max_attempts: int = DEFAULT_MAX_PAGE_ATTEMPTS,
    retry_base_delay_seconds: float = (DEFAULT_RETRY_BASE_DELAY_SECONDS),
    on_detail_completed: Optional[DetailCompletedCallback] = None,
    on_detail_retry: Optional[DetailRetryCallback] = None,
) -> DetailAcquisitionResult:
    """Acquire or resume raw detail pages for unique crawl schools."""

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative.")

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    if retry_base_delay_seconds < 0:
        raise ValueError("retry_base_delay_seconds cannot be negative.")

    crawl = get_crawl_job(
        state_db_path,
        crawl_id,
    )

    if crawl is None:
        raise ValueError(f"Crawl job does not exist: {crawl_id}")

    source_ids = unique_source_detail_ids(
        raw_dir,
        crawl_id,
    )

    candidates_total = len(source_ids)

    completed_before = _count_completed_details(
        state_db_path,
        crawl_id,
        source_ids,
    )

    completed_this_run = 0

    for source_id in source_ids:
        checkpoint = get_detail_fetch(
            state_db_path,
            crawl_id,
            source_id,
        )

        if checkpoint is not None and checkpoint.status == "COMPLETED":
            continue

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            start_detail_fetch(
                state_db_path,
                crawl_id,
                source_id,
                utc_now(),
            )

            try:
                response = fetch_detail_page(
                    client,
                    school_id=source_id,
                )

                response.raise_for_status()

                output_path = raw_detail_path(
                    raw_dir,
                    crawl_id,
                    source_id,
                )

                write_raw_text(
                    output_path,
                    response.text,
                )

                detail = parse_detail_page(
                    response.text,
                    source_detail_id=(source_id),
                )

                if detail.displayed_name is None:
                    raise ValueError("Detail page did not contain a school name.")

                complete_detail_fetch(
                    state_db_path,
                    crawl_id,
                    source_id,
                    http_status=(response.status_code),
                    content_length=len(response.content),
                    completed_at=utc_now(),
                )

                break

            except Exception as exc:
                can_retry = is_retryable_http_error(exc) and attempt < max_attempts

                if can_retry:
                    wait_seconds = retry_delay(
                        retry_base_delay_seconds,
                        attempt,
                    )

                    if on_detail_retry is not None:
                        on_detail_retry(
                            source_id,
                            attempt,
                            max_attempts,
                            wait_seconds,
                            str(exc),
                        )

                    if wait_seconds > 0:
                        time.sleep(wait_seconds)

                    continue

                fail_detail_fetch(
                    state_db_path,
                    crawl_id,
                    source_id,
                    str(exc),
                )

                raise

        completed_this_run += 1

        completed_total = completed_before + completed_this_run

        if on_detail_completed is not None:
            on_detail_completed(
                source_id,
                completed_total,
                candidates_total,
            )

        if completed_this_run >= limit:
            break

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    completed_total = completed_before + completed_this_run

    remaining_total = candidates_total - completed_total

    return DetailAcquisitionResult(
        crawl_id=crawl_id,
        candidates_total=(candidates_total),
        completed_this_run=(completed_this_run),
        completed_total=(completed_total),
        remaining_total=(remaining_total),
    )
