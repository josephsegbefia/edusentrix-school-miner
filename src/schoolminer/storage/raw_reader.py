from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from schoolminer.models.raw import (
    RawDirectoryRecord,
)


def iter_raw_crawl_records(
    raw_dir: Path,
    crawl_id: str,
) -> Iterator[RawDirectoryRecord]:
    """Yield validated raw records from one crawl in page order."""

    pages_dir = raw_dir / "crawls" / crawl_id / "pages"

    page_paths = sorted(pages_dir.glob("page-*.jsonl"))

    for page_path in page_paths:
        with page_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                try:
                    payload = json.loads(stripped_line)

                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {page_path} at line {line_number}.") from exc

                try:
                    record = RawDirectoryRecord.model_validate(payload)

                except ValidationError as exc:
                    raise ValueError(
                        f"Invalid raw record in {page_path} at line {line_number}."
                    ) from exc

                if record.crawl_id != crawl_id:
                    raise ValueError("Raw record crawl ID does not match the requested crawl.")

                yield record
