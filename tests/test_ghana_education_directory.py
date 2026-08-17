import pytest

from schoolminer.sources.ghana_education_directory import (
    extract_antiforgery_token,
)


def test_extract_antiforgery_token() -> None:
    html = """
    <html>
        <body>
            <form id="__AjaxAntiForgeryForm">
                <input
                    name="__RequestVerificationToken"
                    type="hidden"
                    value="test-token-123"
                />
            </form>
        </body>
    </html>
    """

    token = extract_antiforgery_token(html)

    assert token == "test-token-123"


def test_extract_antiforgery_token_fails_when_missing() -> None:
    html = """
    <html>
        <body>
            <p>No token here.</p>
        </body>
    </html>
    """

    with pytest.raises(
        ValueError,
        match="Could not find",
    ):
        extract_antiforgery_token(html)


def test_extract_antiforgery_token_fails_when_empty() -> None:
    html = """
    <html>
        <body>
            <input
                name="__RequestVerificationToken"
                type="hidden"
                value=""
            />
        </body>
    </html>
    """

    with pytest.raises(
        ValueError,
        match="has no value",
    ):
        extract_antiforgery_token(html)
