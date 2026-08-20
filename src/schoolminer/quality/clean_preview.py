from __future__ import annotations

from collections import Counter
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schoolminer.cleaning.schools import (
    clean_directory_school,
)
from schoolminer.cleaning.text import (
    clean_text,
)
from schoolminer.storage.raw_reader import (
    iter_raw_crawl_records,
)


class CleanPreviewFailure(BaseModel):
    """One raw school that could not be deterministically cleaned."""

    model_config = ConfigDict(
        extra="forbid",
    )

    source_detail_id: Optional[str] = None

    page: int = Field(
        ge=1,
    )

    position: int = Field(
        ge=1,
    )

    error_type: str
    error: str


class CleanCrawlPreview(BaseModel):
    """Summary of deterministic cleaning for one raw crawl."""

    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str

    raw_records_total: int = Field(
        ge=0,
    )

    cleaned_records: int = Field(
        ge=0,
    )

    failed_records: int = Field(
        ge=0,
    )

    schools_with_phone_source: int = Field(
        ge=0,
    )

    schools_without_phone_source: int = Field(
        ge=0,
    )

    phone_components_total: int = Field(
        ge=0,
    )

    phone_components_normalized: int = Field(
        ge=0,
    )

    phone_components_unresolved: int = Field(
        ge=0,
    )

    regions_normalized: int = Field(
        ge=0,
    )

    regions_needing_review: int = Field(
        ge=0,
    )

    regions_missing: int = Field(
        ge=0,
    )

    canonical_region_counts: dict[str, int]

    ownership_counts: dict[str, int]

    failures: list[CleanPreviewFailure]


def preview_clean_crawl(
    raw_dir,
    crawl_id: str,
) -> CleanCrawlPreview:
    """Clean one crawl in memory and summarize the results."""

    raw_records_total = 0
    cleaned_records = 0

    schools_with_phone_source = 0
    schools_without_phone_source = 0

    phone_components_total = 0
    phone_components_normalized = 0
    phone_components_unresolved = 0

    regions_normalized = 0
    regions_needing_review = 0
    regions_missing = 0

    canonical_region_counts: Counter[str] = Counter()

    ownership_counts: Counter[str] = Counter()

    failures: list[CleanPreviewFailure] = []

    for record in iter_raw_crawl_records(
        raw_dir,
        crawl_id,
    ):
        raw_records_total += 1

        try:
            school = clean_directory_school(record)

        except ValueError as exc:
            failures.append(
                CleanPreviewFailure(
                    source_detail_id=(record.source_detail_id),
                    page=record.page,
                    position=record.position,
                    error_type=(type(exc).__name__),
                    error=str(exc),
                )
            )

            continue

        cleaned_records += 1

        if clean_text(school.phone_raw) is None:
            schools_without_phone_source += 1

        else:
            schools_with_phone_source += 1

        phone_components_total += len(school.phones)

        for phone in school.phones:
            if phone.normalized is None:
                phone_components_unresolved += 1

            else:
                phone_components_normalized += 1

        region_status = school.location.region_status

        if region_status == "NORMALIZED":
            regions_normalized += 1

        elif region_status == "NEEDS_REVIEW":
            regions_needing_review += 1

        else:
            regions_missing += 1

        if school.location.region is not None:
            canonical_region_counts[school.location.region] += 1

        ownership_counts[school.ownership] += 1

    return CleanCrawlPreview(
        crawl_id=crawl_id,
        raw_records_total=(raw_records_total),
        cleaned_records=(cleaned_records),
        failed_records=len(failures),
        schools_with_phone_source=(schools_with_phone_source),
        schools_without_phone_source=(schools_without_phone_source),
        phone_components_total=(phone_components_total),
        phone_components_normalized=(phone_components_normalized),
        phone_components_unresolved=(phone_components_unresolved),
        regions_normalized=(regions_normalized),
        regions_needing_review=(regions_needing_review),
        regions_missing=(regions_missing),
        canonical_region_counts=dict(sorted(canonical_region_counts.items())),
        ownership_counts=dict(sorted(ownership_counts.items())),
        failures=failures,
    )
