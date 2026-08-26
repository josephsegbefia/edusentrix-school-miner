from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Optional

from schoolminer.cleaning.placeholders import clean_source_value
from schoolminer.models.clean_school import Ownership

DETAIL_OWNERSHIP_MAP = {
    "public": "PUBLIC",
    "private": "PRIVATE",
}


KNOWN_GENDER_MAP = {
    "mixed": "Mixed",
    "boys": "Boys",
    "girls": "Girls",
}


KNOWN_LEVEL_MAP = {
    "creche": "Creche",
    "nursery": "Nursery",
    "kindergarten": "Kindergarten",
    "primary": "Primary",
    "junior high school": "Junior High School",
}


ASSISTANCE_SEPARATOR = re.compile(r"\s*[,;]+\s*")


def normalize_detail_ownership(
    value: Optional[str],
) -> Ownership:
    """
    Normalize ownership displayed on a detail page.

    Unknown or missing values remain UNKNOWN rather
    than being guessed.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return "UNKNOWN"

    return DETAIL_OWNERSHIP_MAP.get(
        cleaned.casefold(),
        "UNKNOWN",
    )


def normalize_gender(
    value: Optional[str],
) -> Optional[str]:
    """
    Normalize known gender labels while preserving
    unfamiliar non-empty source values.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return None

    return KNOWN_GENDER_MAP.get(
        cleaned.casefold(),
        cleaned,
    )


def normalize_levels(
    values: Iterable[str],
) -> list[str]:
    """
    Normalize and deduplicate school levels.

    Known source labels receive canonical spelling.
    Unknown labels are retained rather than discarded.
    """

    normalized = []
    seen = set()

    for value in values:
        cleaned = clean_source_value(value)

        if cleaned is None:
            continue

        canonical = KNOWN_LEVEL_MAP.get(
            cleaned.casefold(),
            cleaned,
        )

        comparison_key = canonical.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)

        normalized.append(canonical)

    return normalized


def normalize_profile_text(
    value: Optional[str],
) -> Optional[str]:
    """
    Normalize an optional profile field.

    Known source placeholders such as N/A become None.
    Other text is whitespace-normalized but otherwise
    preserved.
    """

    return clean_source_value(value)


def normalize_assistance_needed(
    value: Optional[str],
) -> list[str]:
    """
    Convert the source's comma/semicolon-separated
    assistance field into individual normalized values.

    Wording is preserved. We do not yet attempt to
    merge concepts such as 'Computers' and
    'Computers/lab'.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return []

    components = ASSISTANCE_SEPARATOR.split(cleaned)

    normalized = []
    seen = set()

    for component in components:
        item = clean_source_value(component)

        if item is None:
            continue

        comparison_key = item.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)

        normalized.append(item)

    return normalized
