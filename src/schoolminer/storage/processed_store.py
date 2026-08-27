from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from schoolminer.models.enriched_school import (
    EnrichedSchoolCandidate,
)


def processed_crawl_dir(
    data_dir: Path,
    crawl_id: str,
) -> Path:
    """Return the processed directory for one crawl."""

    return (
        data_dir
        / "processed"
        / "crawls"
        / crawl_id
    )


def processed_schools_path(
    data_dir: Path,
    crawl_id: str,
) -> Path:
    """Return the canonical enriched-school JSONL path."""

    return (
        processed_crawl_dir(
            data_dir,
            crawl_id,
        )
        / "schools.jsonl"
    )


def processed_review_path(
    data_dir: Path,
    crawl_id: str,
) -> Path:
    """Return the JSONL path for review-required candidates."""

    return (
        processed_crawl_dir(
            data_dir,
            crawl_id,
        )
        / "review.jsonl"
    )


def write_candidate_jsonl(
    path: Path,
    candidates: Iterable[
        EnrichedSchoolCandidate
    ],
) -> int:
    """
    Atomically write candidates as JSON Lines.

    Returns the number of records written.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None
    count = 0

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(
                file.name
            )

            for candidate in candidates:
                file.write(
                    candidate.model_dump_json()
                )

                file.write(
                    "\n"
                )

                count += 1

            file.flush()

            os.fsync(
                file.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(
                missing_ok=True
            )

        raise

    return count