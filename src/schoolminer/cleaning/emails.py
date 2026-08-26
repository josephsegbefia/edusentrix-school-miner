from __future__ import annotations

import re
from typing import Optional

from schoolminer.cleaning.placeholders import clean_source_value
from schoolminer.models.enriched_school import EnrichedEmail

LOCAL_PART_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")

DOMAIN_LABEL_PATTERN = re.compile(
    r"^[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)


def _is_valid_email(
    value: str,
) -> bool:
    """Apply conservative structural validation to an email address."""

    if len(value) > 254:
        return False

    if value.count("@") != 1:
        return False

    local_part, domain = value.split(
        "@",
        maxsplit=1,
    )

    if not local_part:
        return False

    if not domain:
        return False

    if len(local_part) > 64:
        return False

    if local_part.startswith(".") or local_part.endswith(".") or ".." in local_part:
        return False

    if LOCAL_PART_PATTERN.fullmatch(local_part) is None:
        return False

    if domain.startswith(".") or domain.endswith("."):
        return False

    domain_labels = domain.split(".")

    # These are public-facing school contact
    # addresses, so require a dotted domain.
    if len(domain_labels) < 2:
        return False

    for label in domain_labels:
        if DOMAIN_LABEL_PATTERN.fullmatch(label) is None:
            return False

    return True


def clean_email(
    value: Optional[str],
) -> EnrichedEmail:
    """
    Normalize one source email while preserving its raw value.

    Known source placeholders become MISSING.
    Structurally malformed values become INVALID.
    Valid values retain their local part and normalize
    the domain to lowercase.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return EnrichedEmail(
            raw=value,
            normalized=None,
            status="MISSING",
        )

    if not _is_valid_email(cleaned):
        return EnrichedEmail(
            raw=value,
            normalized=None,
            status="INVALID",
        )

    local_part, domain = cleaned.split(
        "@",
        maxsplit=1,
    )

    normalized = f"{local_part}@{domain.casefold()}"

    return EnrichedEmail(
        raw=value,
        normalized=normalized,
        status="VALID",
    )
