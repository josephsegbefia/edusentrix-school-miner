from schoolminer.cleaning.emails import (
    clean_email,
)


def test_clean_email_accepts_valid_email() -> None:
    email = clean_email("samuelabeebase@gmail.com")

    assert email.raw == "samuelabeebase@gmail.com"

    assert email.normalized == "samuelabeebase@gmail.com"

    assert email.status == "VALID"


def test_clean_email_removes_surrounding_whitespace() -> None:
    email = clean_email("  person@example.com  ")

    assert email.raw == "  person@example.com  "

    assert email.normalized == "person@example.com"

    assert email.status == "VALID"


def test_clean_email_normalizes_domain_case() -> None:
    email = clean_email("Person@GMAIL.COM")

    assert email.normalized == "Person@gmail.com"

    assert email.status == "VALID"


def test_clean_email_treats_na_as_missing() -> None:
    email = clean_email("N/A")

    assert email.raw == "N/A"

    assert email.normalized is None

    assert email.status == "MISSING"


def test_clean_email_treats_blank_as_missing() -> None:
    email = clean_email("")

    assert email.raw == ""

    assert email.normalized is None

    assert email.status == "MISSING"


def test_clean_email_treats_none_as_missing() -> None:
    email = clean_email(None)

    assert email.raw is None
    assert email.normalized is None
    assert email.status == "MISSING"


def test_clean_email_rejects_observed_malformed_email() -> None:
    email = clean_email("felixgyawa.vra.com")

    assert email.raw == "felixgyawa.vra.com"

    assert email.normalized is None

    assert email.status == "INVALID"


def test_clean_email_rejects_internal_whitespace() -> None:
    email = clean_email("person @example.com")

    assert email.normalized is None
    assert email.status == "INVALID"


def test_clean_email_rejects_multiple_at_symbols() -> None:
    email = clean_email("person@@example.com")

    assert email.normalized is None
    assert email.status == "INVALID"
