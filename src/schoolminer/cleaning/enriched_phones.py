from __future__ import annotations

from typing import Optional

from schoolminer.cleaning.phones import clean_phone_field
from schoolminer.cleaning.placeholders import clean_source_value
from schoolminer.cleaning.text import clean_text
from schoolminer.models.enriched_school import EnrichedPhone

PhoneKey = tuple[str, str]


def _phone_key(
    raw: str,
    normalized: Optional[str],
) -> PhoneKey:
    """
    Build a deterministic reconciliation key.

    Valid normalized numbers are matched by their
    normalized E.164 value.

    Unresolved numbers are matched only by their
    cleaned raw representation. We deliberately do
    not guess that differently formatted malformed
    numbers are the same phone.
    """

    if normalized is not None:
        return (
            "normalized",
            normalized,
        )

    cleaned_raw = clean_text(raw)

    if cleaned_raw is None:
        raise ValueError("Phone component cannot be empty.")

    return (
        "raw",
        cleaned_raw.casefold(),
    )


def _phone_components(
    value: Optional[str],
):
    """
    Return usable phone components from one source field.

    Known source placeholders such as N/A are
    interpreted as missing and therefore produce
    no phone components.
    """

    cleaned = clean_source_value(value)

    if cleaned is None:
        return []

    return clean_phone_field(cleaned)


def reconcile_phones(
    listing_phone_raw: Optional[str],
    detail_phone_raw: Optional[str],
) -> list[EnrichedPhone]:
    """
    Reconcile listing and detail phone fields.

    Numbers that normalize to the same value are merged
    while retaining provenance from both source surfaces.

    Unresolved values are retained without attempting
    to repair or infer missing digits.
    """

    phones_by_key: dict[
        PhoneKey,
        EnrichedPhone,
    ] = {}

    phone_order: list[PhoneKey] = []

    def add_source(
        value: Optional[str],
        source: str,
    ) -> None:
        components = _phone_components(value)

        for component in components:
            raw_component = clean_text(component.raw)

            if raw_component is None:
                continue

            key = _phone_key(
                raw_component,
                component.normalized,
            )

            existing = phones_by_key.get(key)

            if existing is None:
                if source == "LISTING":
                    phone = EnrichedPhone(
                        normalized=(component.normalized),
                        listing_raw=(raw_component),
                        detail_raw=None,
                        source="LISTING",
                    )

                elif source == "DETAIL":
                    phone = EnrichedPhone(
                        normalized=(component.normalized),
                        listing_raw=None,
                        detail_raw=(raw_component),
                        source="DETAIL",
                    )

                else:
                    raise ValueError(f"Unsupported phone source: {source}")

                phones_by_key[key] = phone

                phone_order.append(key)

                continue

            listing_raw = existing.listing_raw

            detail_raw = existing.detail_raw

            if source == "LISTING":
                if listing_raw is None:
                    listing_raw = raw_component

            elif source == "DETAIL":
                if detail_raw is None:
                    detail_raw = raw_component

            else:
                raise ValueError(f"Unsupported phone source: {source}")

            if listing_raw is not None and detail_raw is not None:
                merged_source = "LISTING_AND_DETAIL"

            elif listing_raw is not None:
                merged_source = "LISTING"

            else:
                merged_source = "DETAIL"

            phones_by_key[key] = existing.model_copy(
                update={
                    "listing_raw": (listing_raw),
                    "detail_raw": (detail_raw),
                    "source": (merged_source),
                }
            )

    # Listing order is authoritative for ordering.
    # Detail-only numbers are appended afterward.
    add_source(
        listing_phone_raw,
        "LISTING",
    )

    add_source(
        detail_phone_raw,
        "DETAIL",
    )

    return [phones_by_key[key] for key in phone_order]
