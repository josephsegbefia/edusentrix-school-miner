import pytest
from pydantic import ValidationError

from schoolminer.models.directory import (
    DirectoryListing,
    DirectorySearchPage,
)


def test_directory_listing_parses_realistic_record() -> None:
    payload = {
        "InstitutionName": "1 SIGNAL REGIMENT BASIC",
        "InstitutionId": 1109,
        "TownName": "Burma Camp, Accra",
        "Region": "Greater Accra Region",
        "Phone": "0302773029 or 0244826894",
        "OwnerShipId": 2,
        "Logo": ("https://saghedu.blob.core.windows.net/ghedu/institutions/images/1109_ico.png"),
    }

    listing = DirectoryListing.model_validate(payload)

    assert listing.institution_id == 1109
    assert listing.institution_name == "1 SIGNAL REGIMENT BASIC"
    assert listing.town_name == "Burma Camp, Accra"
    assert listing.region == "Greater Accra Region"
    assert listing.phone_raw == "0302773029 or 0244826894"
    assert listing.ownership_id == 2


def test_directory_listing_allows_missing_phone() -> None:
    payload = {
        "InstitutionName": ("28TH FEB. RD PRIMARY & KG PETER ODARTEY LAMPTEY MEMORIAL JHS"),
        "InstitutionId": 16621,
        "TownName": "Accra",
        "Region": "Greater Accra Region",
        "Phone": None,
        "OwnerShipId": 2,
        "Logo": None,
    }

    listing = DirectoryListing.model_validate(payload)

    assert listing.institution_id == 16621
    assert listing.phone_raw is None


def test_directory_listing_requires_id() -> None:
    payload = {
        "InstitutionName": "Example JHS",
    }

    with pytest.raises(ValidationError):
        DirectoryListing.model_validate(payload)


def test_directory_listing_requires_name() -> None:
    payload = {
        "InstitutionId": 1234,
    }

    with pytest.raises(ValidationError):
        DirectoryListing.model_validate(payload)


def test_search_page_parses_records() -> None:
    payload = {
        "Data": [
            {
                "InstitutionName": ("4 BATTALION BASIC SCHOOL"),
                "InstitutionId": 5213,
                "TownName": "Complex Barracks",
                "Region": "Ashanti Region",
                "Phone": "0244572512",
                "OwnerShipId": 2,
                "Logo": "fav.ico",
            },
            {
                "InstitutionName": ("5TH BATTALION PRIMARY/JHS"),
                "InstitutionId": 1114,
                "TownName": "Burma Camp",
                "Region": "Greater Accra Region",
                "Phone": "0244685882",
                "OwnerShipId": 2,
                "Logo": None,
            },
        ],
        "PageCount": 1730,
    }

    search_page = DirectorySearchPage.model_validate(payload)

    assert search_page.page_count == 1730
    assert len(search_page.records) == 2

    assert search_page.records[0].institution_id == 5213

    assert search_page.records[1].institution_id == 1114
