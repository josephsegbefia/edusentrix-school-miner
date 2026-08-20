from __future__ import annotations

from typing import Any

from schoolminer.models.clean_school import (
    Ownership,
)


def normalize_ownership(
    value: Any,
) -> Ownership:
    """Normalize the directory ownership code."""

    if value == 1:
        return "PRIVATE"

    if value == 2:
        return "PUBLIC"

    return "UNKNOWN"
