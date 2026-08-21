from __future__ import annotations

from typing import Optional

from schoolminer.cleaning.text import clean_text

SOURCE_MISSING_MARKERS = frozenset(
    {
        "n/a",
    }
)


def clean_source_value(
    value: Optional[str],
) -> Optional[str]:
    """Clean an optional source value and remove known placeholders."""

    cleaned = clean_text(value)

    if cleaned is None:
        return None

    if cleaned.casefold() in SOURCE_MISSING_MARKERS:
        return None

    return cleaned
