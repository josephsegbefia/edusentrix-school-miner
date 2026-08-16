from urllib.parse import parse_qsl

import httpx

from schoolminer.config import SEARCH_API_URL
from schoolminer.sources.ghana_education_directory import fetch_search_page


def test_fetch_search_page_sends_urlencoded_form_body() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(
            200,
            request=request,
            json={"PageCount": 1, "Data": []},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        response = fetch_search_page(
            client,
            token="token-123",
            page=2,
            region="All",
            search="academy",
            categories=["Junior High School", "STEM"],
        )

    assert response.status_code == 200
    assert captured_request is not None
    assert str(captured_request.url) == SEARCH_API_URL
    assert captured_request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qsl(captured_request.content.decode()) == [
        ("__RequestVerificationToken", "token-123"),
        ("s", "academy"),
        ("Spara[regS]", "All"),
        ("Spara[sort]", "0"),
        ("Spara[page]", "2"),
        ("Spara[catS][]", "Junior High School"),
        ("Spara[catS][]", "STEM"),
    ]
