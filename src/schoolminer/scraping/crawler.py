from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

import httpx

from schoolminer.config import (
    CATEGORY_URL,
    DEFAULT_MAX_PAGE_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY_SECONDS,
    DETAIL_URL_TEMPLATE,
    JHS_CATEGORY,
    SEARCH_API_URL,
)
from schoolminer.models.crawl import CrawlJob
from schoolminer.models.raw import RawDirectoryRecord
from schoolminer.scraping.retry import (
    is_retryable_http_error,
    retry_delay,
)
from schoolminer.sources.ghana_education_directory import (
    SOURCE_NAME,
    extract_antiforgery_token,
    fetch_search_page,
    parse_search_response,
)
from schoolminer.storage.raw_store import (
    raw_page_path,
    write_raw_page,
)
from schoolminer.storage.sqlite_store import (
    complete_crawl_page,
    create_crawl_job,
    fail_crawl_page,
    get_crawl_job,
    set_crawl_total_pages,
    start_crawl_page,
    update_crawl_status,
)

PageCompletedCallback = Callable[
    [int, int, int],
    None,
]

PageRetryCallback = Callable[
    [int, int, int, float, str],
    None,
]


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def generate_crawl_id() -> str:
    """Generate a human-readable unique crawl identifier."""

    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")

    suffix = uuid4().hex[:8]

    return f"ged-jhs-{timestamp}-{suffix}"


def create_directory_crawl(
    state_db_path: Path,
    *,
    region_filter: str = "All",
) -> CrawlJob:
    """Create a new JHS directory crawl job."""

    now = utc_now()

    job = CrawlJob(
        crawl_id=generate_crawl_id(),
        source=SOURCE_NAME,
        category=JHS_CATEGORY,
        region_filter=region_filter,
        status="PENDING",
        created_at=now,
        updated_at=now,
        total_pages=None,
        next_page=1,
        records_saved=0,
        last_error=None,
    )

    create_crawl_job(
        state_db_path,
        job,
    )

    return job


def _build_raw_page_records(
    *,
    crawl: CrawlJob,
    page_number: int,
    fetched_at: datetime,
    raw_records: list[dict],
) -> list[RawDirectoryRecord]:
    """Wrap untouched source records with acquisition provenance."""

    records = []

    for position, raw_record in enumerate(
        raw_records,
        start=1,
    ):
        institution_id = raw_record.get("InstitutionId")

        if institution_id is None:
            raise ValueError("Raw directory record is missing InstitutionId.")

        source_detail_id = str(institution_id)

        records.append(
            RawDirectoryRecord(
                crawl_id=crawl.crawl_id,
                source=crawl.source,
                category=crawl.category,
                region_filter=(crawl.region_filter),
                page=page_number,
                position=position,
                fetched_at=fetched_at,
                source_detail_id=(source_detail_id),
                source_url=SEARCH_API_URL,
                detail_url=(DETAIL_URL_TEMPLATE.format(school_id=(source_detail_id))),
                raw=raw_record,
            )
        )

    return records


def _extract_raw_records(
    response: httpx.Response,
) -> list[dict]:
    """Return the untouched Data array from a validated response."""

    payload = response.json()

    if not isinstance(payload, dict):
        raise TypeError("Directory response is not a JSON object.")

    data = payload.get("Data")

    if not isinstance(data, list):
        raise TypeError("Directory response Data is not a list.")

    for item in data:
        if not isinstance(item, dict):
            raise TypeError("Directory Data contains a non-object record.")

    return data


# RETRYABLE_HTTP_STATUS_CODES = {
#     408,
#     429,
#     500,
#     502,
#     503,
#     504,
# }


# def _is_retryable_page_error(
#     error: Exception,
# ) -> bool:
#     """Return whether a page request failure may be temporary."""

#     if isinstance(
#         error,
#         httpx.TransportError,
#     ):
#         return True

#     if isinstance(
#         error,
#         httpx.HTTPStatusError,
#     ):
#         return error.response.status_code in RETRYABLE_HTTP_STATUS_CODES

#     return False


# def _retry_delay(
#     base_delay_seconds: float,
#     failed_attempt: int,
# ) -> float:
#     """Calculate exponential retry delay after a failed attempt."""

#     return base_delay_seconds * (2 ** (failed_attempt - 1))


def run_directory_crawl(
    client: httpx.Client,
    *,
    state_db_path: Path,
    raw_dir: Path,
    crawl_id: str,
    limit: int,
    delay_seconds: float = 1.0,
    max_attempts: int = DEFAULT_MAX_PAGE_ATTEMPTS,
    retry_base_delay_seconds: float = (DEFAULT_RETRY_BASE_DELAY_SECONDS),
    on_page_completed: Optional[PageCompletedCallback] = None,
    on_page_retry: Optional[PageRetryCallback] = None,
) -> CrawlJob:
    """Run or resume one directory crawl."""

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

    if crawl.status == "COMPLETED":
        return crawl

    update_crawl_status(
        state_db_path,
        crawl_id,
        "RUNNING",
        utc_now(),
    )

    try:
        category_response = client.get(
            CATEGORY_URL,
            params={
                "c": crawl.category,
            },
        )

        category_response.raise_for_status()

        token = extract_antiforgery_token(category_response.text)

    except Exception as exc:
        update_crawl_status(
            state_db_path,
            crawl_id,
            "FAILED",
            utc_now(),
            last_error=str(exc),
        )

        raise

    records_this_run = 0

    while True:
        crawl = get_crawl_job(
            state_db_path,
            crawl_id,
        )

        if crawl is None:
            raise RuntimeError("Crawl disappeared from the state database.")

        if crawl.total_pages is not None and crawl.next_page > crawl.total_pages:
            update_crawl_status(
                state_db_path,
                crawl_id,
                "COMPLETED",
                utc_now(),
            )

            break

        page_number = crawl.next_page

        page_records = None
        search_page = None

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            started_at = utc_now()

            start_crawl_page(
                state_db_path,
                crawl_id,
                page_number,
                started_at,
            )

            try:
                response = fetch_search_page(
                    client,
                    token=token,
                    page=page_number,
                    region=crawl.region_filter,
                    categories=[
                        crawl.category,
                    ],
                )

                search_page = parse_search_response(response)

                raw_records = _extract_raw_records(response)

                if len(raw_records) != len(search_page.records):
                    raise ValueError("Raw and validated record counts do not match.")

                if crawl.total_pages is None:
                    set_crawl_total_pages(
                        state_db_path,
                        crawl_id,
                        search_page.page_count,
                        utc_now(),
                    )

                elif crawl.total_pages != search_page.page_count:
                    raise ValueError(
                        "Directory PageCount "
                        "changed from "
                        f"{crawl.total_pages} "
                        "to "
                        f"{search_page.page_count} "
                        "during this crawl."
                    )

                fetched_at = utc_now()

                page_records = _build_raw_page_records(
                    crawl=crawl,
                    page_number=(page_number),
                    fetched_at=(fetched_at),
                    raw_records=(raw_records),
                )

                output_path = raw_page_path(
                    raw_dir,
                    crawl_id,
                    page_number,
                )

                write_raw_page(
                    output_path,
                    page_records,
                )

                completed_at = utc_now()

                complete_crawl_page(
                    state_db_path,
                    crawl_id,
                    page_number,
                    len(page_records),
                    completed_at,
                )

                break

            except Exception as exc:
                can_retry = is_retryable_http_error(exc) and attempt < max_attempts

                if can_retry:
                    delay = retry_delay(
                        retry_base_delay_seconds,
                        attempt,
                    )

                    if on_page_retry is not None:
                        on_page_retry(
                            page_number,
                            attempt,
                            max_attempts,
                            delay,
                            str(exc),
                        )

                    if delay > 0:
                        time.sleep(delay)

                    continue

                fail_crawl_page(
                    state_db_path,
                    crawl_id,
                    page_number,
                    str(exc),
                    utc_now(),
                )

                raise

        if page_records is None or search_page is None:
            raise RuntimeError("Page processing ended without a completed result.")

        page_record_count = len(page_records)

        records_this_run += page_record_count

        current_crawl = get_crawl_job(
            state_db_path,
            crawl_id,
        )

        if current_crawl is None:
            raise RuntimeError("Crawl disappeared from the state database.")

        total_pages = current_crawl.total_pages or search_page.page_count

        if on_page_completed is not None:
            on_page_completed(
                page_number,
                total_pages,
                page_record_count,
            )

        if current_crawl.next_page > total_pages:
            update_crawl_status(
                state_db_path,
                crawl_id,
                "COMPLETED",
                utc_now(),
            )

            break

        if records_this_run >= limit:
            update_crawl_status(
                state_db_path,
                crawl_id,
                "PAUSED",
                utc_now(),
            )

            break

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    final_crawl = get_crawl_job(
        state_db_path,
        crawl_id,
    )

    if final_crawl is None:
        raise RuntimeError("Crawl disappeared from the state database.")

    return final_crawl
