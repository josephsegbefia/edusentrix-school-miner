from __future__ import annotations

from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from schoolminer.config import JHS_CATEGORY, SEARCH_API_URL


def extract_antiforgery_token(html: str) -> str:
    """Extract the ASP.NET request verification token from category HTML."""

    soup = BeautifulSoup(html, "lxml")

    token_input = soup.find(
        "input",
        attrs={
            "name": "__RequestVerificationToken",
        },
    )

    if token_input is None:
        raise ValueError("Could not find __RequestVerificationToken in the category HTML.")

    token = token_input.get("value")

    if not token:
        raise ValueError("__RequestVerificationToken exists but has no value.")

    return str(token)


def fetch_search_page(
    client: httpx.Client,
    *,
    token: str,
    page: int,
    region: str = "All",
    search: str = "",
    categories: list[str] | None = None,
) -> httpx.Response:
    """Request one structured search-results page."""

    selected_categories = categories if categories is not None else [JHS_CATEGORY]

    form_data: list[tuple[str, str]] = [
        (
            "__RequestVerificationToken",
            token,
        ),
        (
            "s",
            search,
        ),
        (
            "Spara[regS]",
            region,
        ),
        (
            "Spara[sort]",
            "0",
        ),
        (
            "Spara[page]",
            str(page),
        ),
    ]

    for category in selected_categories:
        form_data.append(
            (
                "Spara[catS][]",
                category,
            )
        )

    encoded_form_data = urlencode(form_data)

    return client.post(
        SEARCH_API_URL,
        content=encoded_form_data,
        headers={
            "content-type": "application/x-www-form-urlencoded",
        },
    )
