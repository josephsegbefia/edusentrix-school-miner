from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RawCrawlAudit(BaseModel):
    """Quality summary for one persisted raw crawl."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str

    page_files: int = Field(
        ge=0,
    )

    records_total: int = Field(
        ge=0,
    )

    unique_source_ids: int = Field(
        ge=0,
    )

    duplicate_source_ids: list[str]

    missing_names: int = Field(
        ge=0,
    )

    missing_regions: int = Field(
        ge=0,
    )

    missing_towns: int = Field(
        ge=0,
    )

    missing_phones: int = Field(
        ge=0,
    )

    source_id_mismatches: int = Field(
        ge=0,
    )

    region_counts: dict[str, int]

    ownership_counts: dict[str, int]


def _is_missing(
    value: Any,
) -> bool:
    """Return whether a source value should count as missing."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    return False


def _ownership_label(
    value: Any,
) -> str:
    """Return a readable label for the source ownership code."""

    if value == 1:
        return "Private"

    if value == 2:
        return "Public"

    if value is None:
        return "Missing"

    return f"Unknown:{value}"


def audit_raw_crawl(
    raw_dir: Path,
    crawl_id: str,
) -> RawCrawlAudit:
    """Audit persisted raw page files for one crawl."""

    pages_dir = raw_dir / "crawls" / crawl_id / "pages"

    page_paths = sorted(pages_dir.glob("page-*.jsonl"))

    source_ids: list[str] = []

    missing_names = 0
    missing_regions = 0
    missing_towns = 0
    missing_phones = 0

    source_id_mismatches = 0

    region_counts: Counter[str] = Counter()
    ownership_counts: Counter[str] = Counter()

    records_total = 0

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
                    record = json.loads(stripped_line)

                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {page_path} at line {line_number}.") from exc

                if not isinstance(
                    record,
                    dict,
                ):
                    raise TypeError("Raw page record must be a JSON object.")

                raw = record.get("raw")

                if not isinstance(
                    raw,
                    dict,
                ):
                    raise TypeError("Raw page record is missing its raw object.")

                records_total += 1

                source_detail_id = str(
                    record.get(
                        "source_detail_id",
                        "",
                    )
                )

                source_ids.append(source_detail_id)

                raw_institution_id = raw.get("InstitutionId")

                if source_detail_id != str(raw_institution_id):
                    source_id_mismatches += 1

                name = raw.get("InstitutionName")

                region = raw.get("Region")

                town = raw.get("TownName")

                phone = raw.get("Phone")

                ownership = raw.get("OwnerShipId")

                if _is_missing(name):
                    missing_names += 1

                if _is_missing(region):
                    missing_regions += 1

                else:
                    region_counts[str(region)] += 1

                if _is_missing(town):
                    missing_towns += 1

                if _is_missing(phone):
                    missing_phones += 1

                ownership_counts[_ownership_label(ownership)] += 1

    source_id_counts = Counter(source_ids)

    duplicate_source_ids = sorted(
        source_id for source_id, count in source_id_counts.items() if count > 1
    )

    return RawCrawlAudit(
        crawl_id=crawl_id,
        page_files=len(page_paths),
        records_total=records_total,
        unique_source_ids=len(source_id_counts),
        duplicate_source_ids=(duplicate_source_ids),
        missing_names=missing_names,
        missing_regions=missing_regions,
        missing_towns=missing_towns,
        missing_phones=missing_phones,
        source_id_mismatches=(source_id_mismatches),
        region_counts=dict(sorted(region_counts.items())),
        ownership_counts=dict(sorted(ownership_counts.items())),
    )
