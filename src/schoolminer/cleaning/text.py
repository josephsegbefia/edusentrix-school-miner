from __future__ import annotations

from typing import Optional


def clean_text(
    value: Optional[str],
) -> Optional[str]:
    """Trim text and collapse repeated whitespace."""

    if value is None:
        return None

    cleaned = " ".join(value.split())

    if not cleaned:
        return None

    return cleaned


def clean_required_text(
    value: Optional[str],
    *,
    field_name: str,
) -> str:
    """Clean required text and fail if nothing remains."""

    cleaned = clean_text(value)

    if cleaned is None:
        raise ValueError(f"{field_name} is required.")

    return cleaned
