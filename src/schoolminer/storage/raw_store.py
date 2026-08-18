from __future__ import annotations

from pathlib import Path

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
