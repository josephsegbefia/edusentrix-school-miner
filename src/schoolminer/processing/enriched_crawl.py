from __future__ import annotations

from pathlib import Path

from schoolminer.cleaning.enriched_school import (
    build_enriched_school_candidate,
)
from schoolminer.models.enriched_school import (
    EnrichedSchoolCandidate,
)
from schoolminer.sources.ghana_education_directory import (
    parse_detail_page,
)
from schoolminer.storage.raw_reader import (
    iter_raw_crawl_records,
)
from schoolminer.storage.raw_store import (
    raw_detail_path,
)


def build_enriched_crawl(
    raw_dir: Path,
    crawl_id: str,
) -> list[EnrichedSchoolCandidate]:
    """
    Build processed candidates for every unique source
    school in one crawl.

    Source IDs are deduplicated in first-seen order.
    Every candidate requires a corresponding raw detail
    page.
    """

    listings = {}

    for record in iter_raw_crawl_records(
        raw_dir,
        crawl_id,
    ):
        listings.setdefault(
            record.source_detail_id,
            record,
        )

    candidates = []

    for source_id, listing in listings.items():
        detail_path = raw_detail_path(
            raw_dir,
            crawl_id,
            source_id,
        )

        if not detail_path.exists():
            raise FileNotFoundError(f"Missing detail page for source ID {source_id}: {detail_path}")

        html = detail_path.read_text(encoding="utf-8")

        detail = parse_detail_page(
            html,
            source_detail_id=source_id,
        )

        candidate = build_enriched_school_candidate(
            listing,
            detail,
        )

        candidates.append(candidate)

    return candidates
