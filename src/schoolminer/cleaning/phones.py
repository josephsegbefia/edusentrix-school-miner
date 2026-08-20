from __future__ import annotations

import re
from typing import Optional

from schoolminer.cleaning.text import (
    clean_text,
)
from schoolminer.models.clean_school import (
    CleanPhone,
)

PHONE_SEPARATOR_PATTERN = re.compile(
    r"\s+or\s+|[,;/]+",
    flags=re.IGNORECASE,
)


def normalize_ghana_phone(
    value: str,
) -> Optional[str]:
    """Normalize a recognizable Ghana phone number to E.164."""

    cleaned = clean_text(value)

    if cleaned is None:
        return None

    digits = re.sub(
        r"\D",
        "",
        cleaned,
    )

    if len(digits) == 10 and digits.startswith("0"):
        return "+233" + digits[1:]

    if len(digits) == 12 and digits.startswith("233"):
        return "+" + digits

    return None


def clean_phone_field(
    value: Optional[str],
) -> list[CleanPhone]:
    """Split and normalize a raw directory phone field."""

    cleaned = clean_text(value)

    if cleaned is None:
        return []

    parts = PHONE_SEPARATOR_PATTERN.split(cleaned)

    phones: list[CleanPhone] = []

    seen = set()

    for part in parts:
        raw_component = clean_text(part)

        if raw_component is None:
            continue

        normalized = normalize_ghana_phone(raw_component)

        key = (
            raw_component,
            normalized,
        )

        if key in seen:
            continue

        seen.add(key)

        phones.append(
            CleanPhone(
                raw=raw_component,
                normalized=normalized,
            )
        )

    return phones
