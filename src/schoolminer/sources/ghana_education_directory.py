from __future__ import annotations

from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError
from typing import Optional

from schoolminer.config import DETAIL_URL_TEMPLATE, JHS_CATEGORY, SEARCH_API_URL
from schoolminer.models.directory import DirectorySearchPage
from schoolminer.models.directory_detail import (
    DirectoryDetail,
)

SOURCE_NAME = "ghana_education_directory"


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


def parse_search_response(response: httpx.Response) -> DirectorySearchPage:
    """Validate a directory search response into a typed model."""

    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Directory search endpoint did not return valid JSON.") from exc

    if not isinstance(payload, dict):
        raise TypeError("Directory search endpoint did not return a JSON object.")

    try:
        return DirectorySearchPage.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Directory search response did not match the expected schema.") from exc


def fetch_detail_page(
    client: httpx.Client,
    *,
    school_id: str,
) -> httpx.Response:
    """Fetch one school detail page."""

    detail_url = DETAIL_URL_TEMPLATE.format(school_id=school_id)

    return client.get(detail_url)


def _element_text(
    element,
) -> Optional[str]:
    """Return normalized text from a BeautifulSoup element."""

    if element is None:
        return None

    text = element.get_text(
        " ",
        strip=True,
    )

    if not text:
        return None

    return text


def _extract_detail_table_fields(
    soup: BeautifulSoup,
) -> dict[str, str]:
    """Extract label/value pairs from the school detail table."""

    table = soup.find(
        "table",
        class_="table-user-information",
    )

    if table is None:
        return {}

    fields: dict[str, str] = {}

    for row in table.find_all("tr"):
        cells = row.find_all(
            [
                "td",
                "th",
            ],
            recursive=False,
        )

        if len(cells) < 2:
            continue

        label = cells[0].get_text(
            " ",
            strip=True,
        )

        value = " ".join(
            cells[1]
            .get_text(
                " ",
                strip=True,
            )
            .split()
        )

        if not label:
            continue

        normalized_label = label.strip().rstrip(":").strip().casefold()

        fields[normalized_label] = value

    return fields


def parse_detail_page(
    html: str,
    *,
    source_detail_id: str,
) -> DirectoryDetail:
    """Parse one Ghana Education Directory school detail page."""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    heading = soup.find(
        "h4",
        class_="detail_title",
    )

    displayed_school_id = None
    displayed_name = None

    ownership_raw = None
    gender_raw = None
    levels_raw: list[str] = []
    region_raw = None

    if heading is not None:
        displayed_id_element = heading.find(
            "span",
            class_="label-danger",
        )

        displayed_school_id = _element_text(displayed_id_element)

        name_element = heading.find("b")

        displayed_name = _element_text(name_element)

        parent = heading.parent

        if parent is not None:
            badges = parent.find_all(
                "span",
                class_="label-success",
                recursive=False,
            )

            for badge in badges:
                text = _element_text(badge)

                if text is None:
                    continue

                classes = set(badge.get("class", []))

                if "mixl" in classes:
                    gender_raw = text

                elif "levls" in classes:
                    levels_raw.append(text)

                elif "regl" in classes:
                    region_raw = text

                elif ownership_raw is None:
                    ownership_raw = text

    fields = _extract_detail_table_fields(soup)

    return DirectoryDetail(
        source_detail_id=source_detail_id,
        displayed_school_id=(displayed_school_id),
        displayed_name=(displayed_name),
        ownership_raw=ownership_raw,
        gender_raw=gender_raw,
        levels_raw=levels_raw,
        region_raw=region_raw,
        head_name_raw=fields.get("name of head"),
        phone_raw=fields.get("phone"),
        location_raw=fields.get("location"),
        postal_address_raw=fields.get("postal address"),
        email_raw=fields.get("email"),
        district_raw=fields.get("district"),
        assistance_needed_raw=(fields.get("assistance needed")),
    )
