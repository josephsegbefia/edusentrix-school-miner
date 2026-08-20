from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from schoolminer.cleaning.schools import (
    clean_directory_school,
)
from schoolminer.models.clean_school import (
    CleanDirectorySchool,
)
from schoolminer.storage.raw_reader import (
    iter_raw_crawl_records,
)


class SourceDuplicateOccurrence(BaseModel):
    """One repeated observation of a source school."""

    model_config = ConfigDict(
        extra="forbid",
    )

    source_detail_id: str

    kept_page: int = Field(
        ge=1,
    )

    kept_position: int = Field(
        ge=1,
    )

    duplicate_page: int = Field(
        ge=1,
    )

    duplicate_position: int = Field(
        ge=1,
    )

    identical_raw_payload: bool


class SourceIdDedupeResult(BaseModel):
    """Result of deterministic source-ID deduplication."""

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    crawl_id: str

    observations_total: int = Field(
        ge=0,
    )

    unique_schools_total: int = Field(
        ge=0,
    )

    duplicate_observations_total: int = Field(
        ge=0,
    )

    schools: list[CleanDirectorySchool]

    duplicates: list[SourceDuplicateOccurrence]


def dedupe_crawl_by_source_id(
    raw_dir,
    crawl_id: str,
) -> SourceIdDedupeResult:
    """Deduplicate one crawl using the source's stable school ID."""

    seen = {}

    schools = []
    duplicates = []

    observations_total = 0

    for record in iter_raw_crawl_records(
        raw_dir,
        crawl_id,
    ):
        observations_total += 1

        source_detail_id = record.source_detail_id

        existing = seen.get(source_detail_id)

        if existing is None:
            school = clean_directory_school(record)

            seen[source_detail_id] = record

            schools.append(school)

            continue

        duplicates.append(
            SourceDuplicateOccurrence(
                source_detail_id=(source_detail_id),
                kept_page=existing.page,
                kept_position=(existing.position),
                duplicate_page=(record.page),
                duplicate_position=(record.position),
                identical_raw_payload=(existing.raw == record.raw),
            )
        )

    return SourceIdDedupeResult(
        crawl_id=crawl_id,
        observations_total=(observations_total),
        unique_schools_total=len(schools),
        duplicate_observations_total=len(duplicates),
        schools=schools,
        duplicates=duplicates,
    )
