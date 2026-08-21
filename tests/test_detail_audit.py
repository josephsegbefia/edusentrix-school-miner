from __future__ import annotations

from datetime import datetime, timezone

from schoolminer.models.raw import (
    RawDirectoryRecord,
)
from schoolminer.quality.detail_audit import (
    audit_detail_crawl,
)
from schoolminer.storage.raw_store import (
    raw_detail_path,
    raw_page_path,
    write_raw_page,
    write_raw_text,
)


def build_listing(
    *,
    crawl_id: str,
    source_detail_id: str,
    name: str,
    region: str = "Greater Accra Region",
    phone: str | None = "0244000000",
    ownership_id: int = 2,
    position: int = 1,
) -> RawDirectoryRecord:
    return RawDirectoryRecord(
        crawl_id=crawl_id,
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=1,
        position=position,
        fetched_at=datetime(
            2026,
            8,
            21,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        source_detail_id=(source_detail_id),
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": name,
            "InstitutionId": int(source_detail_id),
            "TownName": "Accra",
            "Region": region,
            "Phone": phone,
            "OwnerShipId": ownership_id,
            "Logo": None,
        },
    )


def build_detail_html(
    *,
    displayed_id: str,
    name: str,
    ownership: str = "Public",
    region: str = "Greater Accra Region",
    phone: str = "0244000000",
    email: str = "N/A",
    district: str = "Accra Metro",
) -> str:
    return f"""
    <html>
        <body>
            <div>
                <h4 class="detail_title">
                    <span class="label label-danger">
                        {displayed_id}
                    </span>

                    <b>
                        {name}
                    </b>
                </h4>

                <span class="label label-success">
                    {ownership}
                </span>

                <span class="label label-success mixl">
                    Mixed
                </span>

                <span class="label label-success levls">
                    Primary
                </span>

                <span class="label label-success levls">
                    Junior High School
                </span>

                <span class="label label-success regl">
                    {region}
                </span>

                <table class="table table-user-information">
                    <tr>
                        <td>
                            <strong>Name Of Head:</strong>
                        </td>
                        <td>
                            Test Head
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Phone :</strong>
                        </td>
                        <td>
                            {phone}
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Postal Address :</strong>
                        </td>
                        <td>
                            P. O. Box 123
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Email :</strong>
                        </td>
                        <td>
                            {email}
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>District :</strong>
                        </td>
                        <td>
                            {district}
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Assistance Needed :</strong>
                        </td>
                        <td>
                            Computers
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """


def test_detail_audit_counts_complete_record(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    listing = build_listing(
        crawl_id=crawl_id,
        source_detail_id="1109",
        name="TEST SCHOOL",
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            listing,
        ],
    )

    write_raw_text(
        raw_detail_path(
            tmp_path,
            crawl_id,
            "1109",
        ),
        build_detail_html(
            displayed_id="3959",
            name="TEST SCHOOL",
        ),
    )

    report = audit_detail_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.candidates_total == 1
    assert report.detail_files_total == 1
    assert report.parsed_details == 1
    assert report.failed_details == 0

    assert report.name_matches == 1
    assert report.region_matches == 1
    assert report.phone_matches == 1
    assert report.ownership_matches == 1

    assert report.head_names_present == 1
    assert report.districts_present == 1

    assert report.email_nonblank_without_at_counts == {}

    assert report.level_counts == {
        "Junior High School": 1,
        "Primary": 1,
    }


def test_detail_audit_reports_source_conflicts(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    listing = build_listing(
        crawl_id=crawl_id,
        source_detail_id="1109",
        name="LISTING SCHOOL",
        region="Greater Accra Region",
        phone="0244000000",
        ownership_id=2,
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            listing,
        ],
    )

    write_raw_text(
        raw_detail_path(
            tmp_path,
            crawl_id,
            "1109",
        ),
        build_detail_html(
            displayed_id="3959",
            name="DIFFERENT SCHOOL",
            ownership="Private",
            region="Eastern Region",
            phone="0205000000",
        ),
    )

    report = audit_detail_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.name_mismatches == 1
    assert report.region_mismatches == 1
    assert report.phone_mismatches == 1
    assert report.ownership_mismatches == 1

    assert {issue.field for issue in report.comparison_issues} == {
        "name",
        "region",
        "phone",
        "ownership",
    }


def test_detail_audit_reports_missing_detail_file(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    listing = build_listing(
        crawl_id=crawl_id,
        source_detail_id="1109",
        name="TEST SCHOOL",
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            listing,
        ],
    )

    report = audit_detail_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.candidates_total == 1

    assert report.missing_detail_files == [
        "1109",
    ]

    assert report.parsed_details == 0


def test_detail_audit_treats_na_phone_as_missing(
    tmp_path,
) -> None:
    crawl_id = "test-crawl"

    listing = build_listing(
        crawl_id=crawl_id,
        source_detail_id="1109",
        name="TEST SCHOOL",
        phone=None,
    )

    write_raw_page(
        raw_page_path(
            tmp_path,
            crawl_id,
            1,
        ),
        [
            listing,
        ],
    )

    write_raw_text(
        raw_detail_path(
            tmp_path,
            crawl_id,
            "1109",
        ),
        build_detail_html(
            displayed_id="3959",
            name="TEST SCHOOL",
            phone="N/A",
            email="N/A",
        ),
    )

    report = audit_detail_crawl(
        tmp_path,
        crawl_id,
    )

    assert report.phones_present == 0
    assert report.phones_missing == 1

    assert report.listing_phone_missing_detail_present == 0

    assert report.phone_missing_both == 1

    assert report.emails_blank_or_missing == 1

    assert report.email_nonblank_without_at_counts == {}
