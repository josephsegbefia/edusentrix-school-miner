from urllib.parse import parse_qs

import httpx
import pytest

from schoolminer.sources.ghana_education_directory import (
    extract_antiforgery_token,
    fetch_search_page,
    parse_search_response,
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


def test_fetch_search_page_builds_expected_form_payload() -> None:
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["content_type"] = request.headers.get("content-type")
        captured_request["body"] = request.content.decode("utf-8")

        return httpx.Response(
            200,
            json={
                "Data": [],
                "PageCount": 1,
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        response = fetch_search_page(
            client,
            token="test-token-123",
            page=2,
            region="Greater Accra Region",
        )

    assert response.status_code == 200

    assert captured_request["method"] == "POST"

    assert captured_request["url"].endswith("/search/searchs")

    assert captured_request["content_type"] == "application/x-www-form-urlencoded"

    form_data = parse_qs(
        captured_request["body"],
        keep_blank_values=True,
    )

    assert form_data == {
        "__RequestVerificationToken": [
            "test-token-123",
        ],
        "s": [
            "",
        ],
        "Spara[regS]": [
            "Greater Accra Region",
        ],
        "Spara[sort]": [
            "0",
        ],
        "Spara[page]": [
            "2",
        ],
        "Spara[catS][]": [
            "Junior High School",
        ],
    }


def test_parse_search_response_returns_typed_model() -> None:
    request = httpx.Request(
        "POST",
        "https://ghanaeducation.gov.gh/search/searchs",
    )

    response = httpx.Response(
        200,
        request=request,
        json={
            "Data": [
                {
                    "InstitutionName": "4 BATTALION BASIC SCHOOL",
                    "InstitutionId": 5213,
                    "TownName": "Complex Barracks",
                    "Region": "Ashanti Region",
                    "Phone": "0244572512",
                    "OwnerShipId": 2,
                    "Logo": "fav.ico",
                }
            ],
            "PageCount": 1730,
        },
    )

    search_page = parse_search_response(response)
    assert search_page.page_count == 1730
    assert len(search_page.records) == 1

    assert search_page.records[0].institution_id == 5213


def test_parse_search_response_rejects_invalid_json() -> None:
    request = httpx.Request("POST", "https://ghanaeducation.gov.gh/search/searchs")
    response = httpx.Response(200, request=request, content=b"<html>Not JSON</html>")

    with pytest.raises(ValueError, match="did not return valid JSON."):
        parse_search_response(response)


def test_parse_search_response_rejects_invalid_schema() -> None:
    request = httpx.Request(
        "POST",
        "https://ghanaeducation.gov.gh/search/searchs",
    )
    response = httpx.Response(200, request=request, json={"unexpected": "payload"})

    with pytest.raises(ValueError, match="did not match the expected schema."):
        parse_search_response(response)
