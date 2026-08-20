from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from schoolminer.models.raw import RawDirectoryRecord


def append_raw_record(
    path: Path,
    record: RawDirectoryRecord,
) -> None:
    """Append one raw acquisition record as a JSONL line."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(record.model_dump_json())
        file.write("\n")


def raw_page_path(
    raw_dir: Path,
    crawl_id: str,
    page_number: int,
) -> Path:
    """Return the deterministic raw file path for one crawl page."""

    if page_number < 1:
        raise ValueError("page_number must be at least 1.")

    return raw_dir / "crawls" / crawl_id / "pages" / f"page-{page_number:05d}.jsonl"


def _validate_page_records(
    records: list[RawDirectoryRecord],
) -> None:
    """Ensure one raw page file contains records from one crawl page."""

    if not records:
        return

    expected_crawl_id = records[0].crawl_id
    expected_page = records[0].page

    for record in records:
        if record.crawl_id != expected_crawl_id or record.page != expected_page:
            raise ValueError(
                "All records in a raw page file must belong to the same crawl and page."
            )


def write_raw_page(
    path: Path,
    records: list[RawDirectoryRecord],
) -> None:
    """Atomically write one complete source page as JSONL."""

    _validate_page_records(records)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)

            for record in records:
                file.write(record.model_dump_json())

                file.write("\n")

            file.flush()

            os.fsync(file.fileno())

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        raise


def raw_detail_path(
    raw_dir: Path,
    crawl_id: str,
    source_detail_id: str,
) -> Path:
    """Return the deterministic raw HTML path for one school detail."""

    if not source_detail_id.strip():
        raise ValueError("source_detail_id cannot be empty.")

    return raw_dir / "crawls" / crawl_id / "details" / f"{source_detail_id}.html"


def write_raw_text(
    path: Path,
    content: str,
) -> None:
    """Atomically write raw source text."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)

            file.write(content)

            file.flush()

            os.fsync(file.fileno())

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        raise
