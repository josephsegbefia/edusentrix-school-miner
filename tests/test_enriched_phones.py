from schoolminer.cleaning.enriched_phones import (
    reconcile_phones,
)


def test_reconcile_phones_merges_same_normalized_number() -> None:
    phones = reconcile_phones(
        "0244 123 456",
        "0244123456",
    )

    assert len(phones) == 1

    phone = phones[0]

    assert phone.normalized == "+233244123456"

    assert phone.listing_raw == "0244 123 456"

    assert phone.detail_raw == "0244123456"

    assert phone.source == "LISTING_AND_DETAIL"


def test_reconcile_phones_merges_multiple_matching_numbers() -> None:
    phones = reconcile_phones(
        ("0302773029 or 0244826894"),
        ("0302773029 or 0244826894"),
    )

    assert len(phones) == 2

    assert [phone.normalized for phone in phones] == [
        "+233302773029",
        "+233244826894",
    ]

    assert all(phone.source == "LISTING_AND_DETAIL" for phone in phones)


def test_reconcile_phones_preserves_listing_only_number() -> None:
    phones = reconcile_phones(
        "0244123456",
        None,
    )

    assert len(phones) == 1

    phone = phones[0]

    assert phone.normalized == "+233244123456"

    assert phone.listing_raw == "0244123456"

    assert phone.detail_raw is None

    assert phone.source == "LISTING"


def test_reconcile_phones_preserves_detail_only_number() -> None:
    phones = reconcile_phones(
        None,
        "0205123456",
    )

    assert len(phones) == 1

    phone = phones[0]

    assert phone.normalized == "+233205123456"

    assert phone.listing_raw is None

    assert phone.detail_raw == "0205123456"

    assert phone.source == "DETAIL"


def test_reconcile_phones_ignores_source_placeholder() -> None:
    phones = reconcile_phones(
        None,
        "N/A",
    )

    assert phones == []


def test_reconcile_phones_handles_both_sources_missing() -> None:
    phones = reconcile_phones(
        None,
        None,
    )

    assert phones == []


def test_reconcile_phones_preserves_unresolved_number() -> None:
    phones = reconcile_phones(
        "02438233214",
        "02438233214",
    )

    assert len(phones) == 1

    phone = phones[0]

    assert phone.normalized is None

    assert phone.listing_raw == "02438233214"

    assert phone.detail_raw == "02438233214"

    assert phone.source == "LISTING_AND_DETAIL"


def test_reconcile_phones_does_not_invent_missing_digit() -> None:
    phones = reconcile_phones(
        "026353622",
        "026353622",
    )

    assert len(phones) == 1

    assert phones[0].normalized is None

    assert phones[0].listing_raw == "026353622"

    assert phones[0].detail_raw == "026353622"


def test_reconcile_phones_appends_detail_only_additional_number() -> None:
    phones = reconcile_phones(
        "0244123456",
        ("0244123456 or 0205123456"),
    )

    assert len(phones) == 2

    first = phones[0]
    second = phones[1]

    assert first.normalized == "+233244123456"

    assert first.source == "LISTING_AND_DETAIL"

    assert second.normalized == "+233205123456"

    assert second.source == "DETAIL"
