from schoolminer.cleaning.profile import (
    normalize_assistance_needed,
    normalize_detail_ownership,
    normalize_gender,
    normalize_levels,
    normalize_profile_text,
)


def test_normalize_detail_ownership() -> None:
    assert normalize_detail_ownership("Public") == "PUBLIC"

    assert normalize_detail_ownership("Private") == "PRIVATE"

    assert normalize_detail_ownership("Something Else") == "UNKNOWN"

    assert normalize_detail_ownership("N/A") == "UNKNOWN"


def test_normalize_gender() -> None:
    assert normalize_gender(" mixed ") == "Mixed"

    assert normalize_gender("N/A") is None


def test_normalize_gender_preserves_unknown_value() -> None:
    assert normalize_gender("Co-Educational") == "Co-Educational"


def test_normalize_levels_canonicalizes_and_deduplicates() -> None:
    levels = normalize_levels(
        [
            "Primary",
            " junior high school ",
            "PRIMARY",
            "N/A",
        ]
    )

    assert levels == [
        "Primary",
        "Junior High School",
    ]


def test_normalize_levels_preserves_unknown_level() -> None:
    levels = normalize_levels(
        [
            "Technical Programme",
        ]
    )

    assert levels == [
        "Technical Programme",
    ]


def test_normalize_profile_text_handles_source_placeholders() -> None:
    assert normalize_profile_text("  Accra Metro  ") == "Accra Metro"

    assert normalize_profile_text("N/A") is None

    assert normalize_profile_text("") is None

    assert normalize_profile_text(None) is None


def test_normalize_assistance_needed_splits_source_list() -> None:
    assistance = normalize_assistance_needed(
        "Water, Library, BDT Workshop, Science Lab, Pavement Blocks"
    )

    assert assistance == [
        "Water",
        "Library",
        "BDT Workshop",
        "Science Lab",
        "Pavement Blocks",
    ]


def test_normalize_assistance_needed_supports_semicolons() -> None:
    assistance = normalize_assistance_needed("Computers; Library; Water")

    assert assistance == [
        "Computers",
        "Library",
        "Water",
    ]


def test_normalize_assistance_needed_deduplicates_case_insensitively() -> None:
    assistance = normalize_assistance_needed("Library, library, Water")

    assert assistance == [
        "Library",
        "Water",
    ]


def test_normalize_assistance_needed_handles_missing_value() -> None:
    assert normalize_assistance_needed("N/A") == []

    assert normalize_assistance_needed(None) == []
