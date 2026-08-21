from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schoolminer.cleaning.locations import (
    normalize_region,
)
from schoolminer.cleaning.phones import (
    clean_phone_field,
)
from schoolminer.cleaning.placeholders import (
    clean_source_value,
)
from schoolminer.cleaning.text import (
    clean_text,
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


class DetailAuditFailure(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source_detail_id: str
    error_type: str
    error: str


class DetailComparisonIssue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source_detail_id: str
    field: str
    listing_value: Optional[str] = None
    detail_value: Optional[str] = None


class DetailCrawlAudit(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    crawl_id: str

    candidates_total: int = Field(
        ge=0,
    )

    detail_files_total: int = Field(
        ge=0,
    )

    parsed_details: int = Field(
        ge=0,
    )

    failed_details: int = Field(
        ge=0,
    )

    missing_detail_files: list[str]
    unexpected_detail_files: list[str]

    displayed_school_ids_present: int = Field(
        ge=0,
    )

    displayed_school_ids_missing: int = Field(
        ge=0,
    )

    duplicate_displayed_school_ids: list[str]

    head_names_present: int = Field(
        ge=0,
    )

    head_names_missing: int = Field(
        ge=0,
    )

    phones_present: int = Field(
        ge=0,
    )

    phones_missing: int = Field(
        ge=0,
    )

    emails_with_at_sign: int = Field(
        ge=0,
    )

    emails_blank_or_missing: int = Field(
        ge=0,
    )

    email_nonblank_without_at_counts: dict[
        str,
        int,
    ]

    districts_present: int = Field(
        ge=0,
    )

    districts_missing: int = Field(
        ge=0,
    )

    unique_districts: int = Field(
        ge=0,
    )

    postal_addresses_present: int = Field(
        ge=0,
    )

    postal_addresses_missing: int = Field(
        ge=0,
    )

    assistance_present: int = Field(
        ge=0,
    )

    assistance_missing: int = Field(
        ge=0,
    )

    gender_counts: dict[str, int]
    level_counts: dict[str, int]

    name_matches: int = Field(
        ge=0,
    )

    name_mismatches: int = Field(
        ge=0,
    )

    region_matches: int = Field(
        ge=0,
    )

    region_mismatches: int = Field(
        ge=0,
    )

    phone_matches: int = Field(
        ge=0,
    )

    phone_mismatches: int = Field(
        ge=0,
    )

    listing_phone_missing_detail_present: int = Field(
        ge=0,
    )

    listing_phone_present_detail_missing: int = Field(
        ge=0,
    )

    phone_missing_both: int = Field(
        ge=0,
    )

    ownership_matches: int = Field(
        ge=0,
    )

    ownership_mismatches: int = Field(
        ge=0,
    )

    ambiguous_region_district_counts: dict[
        str,
        dict[str, int],
    ]

    comparison_issues: list[DetailComparisonIssue]

    failures: list[DetailAuditFailure]


def _string_value(
    value: object,
) -> Optional[str]:
    if isinstance(
        value,
        str,
    ):
        return value

    return None


def _normalized_text(
    value: Optional[str],
) -> Optional[str]:
    cleaned = clean_text(value)

    if cleaned is None:
        return None

    return cleaned.casefold()


def _listing_ownership_label(
    value: object,
) -> Optional[str]:
    if value == 1:
        return "private"

    if value == 2:
        return "public"

    if value is None:
        return None

    return str(value).casefold()


def _phone_signature(
    value: Optional[str],
) -> Optional[
    tuple[
        tuple[str, str],
        ...,
    ]
]:
    cleaned = clean_source_value(value)

    if cleaned is None:
        return None

    signature = []

    for phone in clean_phone_field(cleaned):
        if phone.normalized is not None:
            signature.append(
                (
                    "normalized",
                    phone.normalized,
                )
            )

            continue

        raw = clean_text(phone.raw)

        if raw is not None:
            signature.append(
                (
                    "raw",
                    raw.casefold(),
                )
            )

    if not signature:
        return None

    return tuple(sorted(signature))


def audit_detail_crawl(
    raw_dir: Path,
    crawl_id: str,
) -> DetailCrawlAudit:
    """Audit enriched detail data for one listing crawl."""

    listing_records = {}

    for record in iter_raw_crawl_records(
        raw_dir,
        crawl_id,
    ):
        listing_records.setdefault(
            record.source_detail_id,
            record,
        )

    source_ids = list(listing_records)

    expected_ids = set(source_ids)

    details_dir = raw_dir / "crawls" / crawl_id / "details"

    detail_paths = {path.stem: path for path in sorted(details_dir.glob("*.html"))}

    actual_ids = set(detail_paths)

    missing_detail_files = sorted(expected_ids - actual_ids)

    unexpected_detail_files = sorted(actual_ids - expected_ids)

    displayed_id_counts = Counter()

    gender_counts = Counter()
    level_counts = Counter()
    district_counts = Counter()

    email_nonblank_without_at_counts = Counter()

    ambiguous_region_district_counts = defaultdict(Counter)

    parsed_details = 0
    failed_details = 0

    displayed_school_ids_present = 0
    displayed_school_ids_missing = 0

    head_names_present = 0
    head_names_missing = 0

    phones_present = 0
    phones_missing = 0

    emails_with_at_sign = 0
    emails_blank_or_missing = 0

    districts_present = 0
    districts_missing = 0

    postal_addresses_present = 0
    postal_addresses_missing = 0

    assistance_present = 0
    assistance_missing = 0

    name_matches = 0
    name_mismatches = 0

    region_matches = 0
    region_mismatches = 0

    phone_matches = 0
    phone_mismatches = 0

    listing_phone_missing_detail_present = 0
    listing_phone_present_detail_missing = 0
    phone_missing_both = 0

    ownership_matches = 0
    ownership_mismatches = 0

    comparison_issues = []
    failures = []

    for source_id in source_ids:
        path = raw_detail_path(
            raw_dir,
            crawl_id,
            source_id,
        )

        if not path.exists():
            continue

        try:
            detail = parse_detail_page(
                path.read_text(encoding="utf-8"),
                source_detail_id=(source_id),
            )

        except (ValueError, TypeError) as exc:
            failed_details += 1

            failures.append(
                DetailAuditFailure(
                    source_detail_id=(source_id),
                    error_type=(type(exc).__name__),
                    error=str(exc),
                )
            )

            continue

        parsed_details += 1

        listing = listing_records[source_id]

        raw = listing.raw

        displayed_school_id = clean_source_value(detail.displayed_school_id)

        if displayed_school_id is None:
            displayed_school_ids_missing += 1

        else:
            displayed_school_ids_present += 1

            displayed_id_counts[detail.displayed_school_id] += 1

        head_name = clean_source_value(detail.head_name_raw)

        if head_name is None:
            head_names_missing += 1

        else:
            head_names_present += 1

        detail_phone_value = clean_source_value(detail.phone_raw)

        if detail_phone_value is None:
            phones_missing += 1

        else:
            phones_present += 1

        email = clean_source_value(detail.email_raw)

        if email is None:
            emails_blank_or_missing += 1

        elif "@" in email:
            emails_with_at_sign += 1

        else:
            email_nonblank_without_at_counts[email] += 1

        district = clean_source_value(detail.district_raw)

        if district is None:
            districts_missing += 1

        else:
            districts_present += 1

            district_counts[district] += 1

        postal_address = clean_source_value(detail.postal_address_raw)

        if postal_address is None:
            postal_addresses_missing += 1

        else:
            postal_addresses_present += 1

        assistance_needed = clean_source_value(detail.assistance_needed_raw)

        if assistance_needed is None:
            assistance_missing += 1

        else:
            assistance_present += 1

        gender = clean_source_value(detail.gender_raw)

        if gender is not None:
            gender_counts[gender] += 1

        for level in detail.levels_raw:
            cleaned_level = clean_source_value(level)

            if cleaned_level is not None:
                level_counts[cleaned_level] += 1

        listing_name = _string_value(raw.get("InstitutionName"))

        detail_name = detail.displayed_name

        if _normalized_text(listing_name) == _normalized_text(detail_name):
            name_matches += 1

        else:
            name_mismatches += 1

            comparison_issues.append(
                DetailComparisonIssue(
                    source_detail_id=(source_id),
                    field="name",
                    listing_value=(listing_name),
                    detail_value=(detail_name),
                )
            )

        listing_region = _string_value(raw.get("Region"))

        detail_region = detail.region_raw

        if _normalized_text(listing_region) == _normalized_text(detail_region):
            region_matches += 1

        else:
            region_mismatches += 1

            comparison_issues.append(
                DetailComparisonIssue(
                    source_detail_id=(source_id),
                    field="region",
                    listing_value=(listing_region),
                    detail_value=(detail_region),
                )
            )

        listing_phone = _string_value(raw.get("Phone"))

        detail_phone = detail.phone_raw

        listing_signature = _phone_signature(listing_phone)

        detail_signature = _phone_signature(detail_phone)

        if listing_signature is None and detail_signature is None:
            phone_missing_both += 1

        elif listing_signature is None and detail_signature is not None:
            (listing_phone_missing_detail_present) += 1

        elif listing_signature is not None and detail_signature is None:
            (listing_phone_present_detail_missing) += 1

        elif listing_signature == detail_signature:
            phone_matches += 1

        else:
            phone_mismatches += 1

            comparison_issues.append(
                DetailComparisonIssue(
                    source_detail_id=(source_id),
                    field="phone",
                    listing_value=(listing_phone),
                    detail_value=(detail_phone),
                )
            )

        listing_ownership = _listing_ownership_label(raw.get("OwnerShipId"))

        detail_ownership = _normalized_text(detail.ownership_raw)

        if listing_ownership == detail_ownership:
            ownership_matches += 1

        else:
            ownership_mismatches += 1

            comparison_issues.append(
                DetailComparisonIssue(
                    source_detail_id=(source_id),
                    field="ownership",
                    listing_value=(listing_ownership),
                    detail_value=(clean_source_value(detail.ownership_raw)),
                )
            )

        region_for_review = clean_source_value(detail.region_raw) or clean_source_value(
            listing_region
        )

        _, region_status = normalize_region(region_for_review)

        if region_status == "NEEDS_REVIEW":
            region_key = region_for_review or "<missing>"

            district_key = district or "<missing>"

            ambiguous_region_district_counts[region_key][district_key] += 1

    duplicate_displayed_school_ids = sorted(
        displayed_id for displayed_id, count in displayed_id_counts.items() if count > 1
    )

    return DetailCrawlAudit(
        crawl_id=crawl_id,
        candidates_total=len(source_ids),
        detail_files_total=len(detail_paths),
        parsed_details=(parsed_details),
        failed_details=(failed_details),
        missing_detail_files=(missing_detail_files),
        unexpected_detail_files=(unexpected_detail_files),
        displayed_school_ids_present=(displayed_school_ids_present),
        displayed_school_ids_missing=(displayed_school_ids_missing),
        duplicate_displayed_school_ids=(duplicate_displayed_school_ids),
        head_names_present=(head_names_present),
        head_names_missing=(head_names_missing),
        phones_present=(phones_present),
        phones_missing=(phones_missing),
        emails_with_at_sign=(emails_with_at_sign),
        emails_blank_or_missing=(emails_blank_or_missing),
        email_nonblank_without_at_counts=dict(sorted(email_nonblank_without_at_counts.items())),
        districts_present=(districts_present),
        districts_missing=(districts_missing),
        unique_districts=len(district_counts),
        postal_addresses_present=(postal_addresses_present),
        postal_addresses_missing=(postal_addresses_missing),
        assistance_present=(assistance_present),
        assistance_missing=(assistance_missing),
        gender_counts=dict(sorted(gender_counts.items())),
        level_counts=dict(sorted(level_counts.items())),
        name_matches=name_matches,
        name_mismatches=(name_mismatches),
        region_matches=(region_matches),
        region_mismatches=(region_mismatches),
        phone_matches=(phone_matches),
        phone_mismatches=(phone_mismatches),
        listing_phone_missing_detail_present=(listing_phone_missing_detail_present),
        listing_phone_present_detail_missing=(listing_phone_present_detail_missing),
        phone_missing_both=(phone_missing_both),
        ownership_matches=(ownership_matches),
        ownership_mismatches=(ownership_mismatches),
        ambiguous_region_district_counts={
            region: dict(sorted(districts.items()))
            for region, districts in sorted(ambiguous_region_district_counts.items())
        },
        comparison_issues=(comparison_issues),
        failures=failures,
    )
