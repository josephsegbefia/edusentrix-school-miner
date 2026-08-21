from schoolminer.cleaning.placeholders import (
    clean_source_value,
)


def test_clean_source_value_treats_na_as_missing() -> None:
    assert clean_source_value("N/A") is None


def test_clean_source_value_treats_blank_as_missing() -> None:
    assert clean_source_value("   ") is None


def test_clean_source_value_preserves_real_value() -> None:
    assert clean_source_value("  Accra Metro  ") == "Accra Metro"
