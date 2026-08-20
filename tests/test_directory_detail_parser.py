from schoolminer.sources.ghana_education_directory import (
    parse_detail_page,
)


DETAIL_HTML = """
<html>
    <body>
        <div>
            <h4 class="detail_title">
                <span class="label label-danger">
                    3959
                </span>

                <b style="color:darkblue">
                    1 SIGNAL REGIMENT BASIC
                </b>
            </h4>

            <span class="label label-success">
                Public
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
                Greater Accra Region
            </span>

            <table class="table table-user-information">
                <tbody>
                    <tr>
                        <td>
                            <strong>Name Of Head:</strong>
                        </td>
                        <td>
                            Mr. Awuku Larbi
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Phone :</strong>
                        </td>
                        <td>
                            0302773029 or 0244826894
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Location:</strong>
                        </td>
                        <td>
                            Burma Camp, Accra
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Postal Address :</strong>
                        </td>
                        <td>
                            P. O. Box 251
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Email :</strong>
                        </td>
                        <td>
                            N/A
                        </td>
                    </tr>

                    <tr></tr>

                    <tr>
                        <td>
                            <strong>District :</strong>
                        </td>
                        <td>
                            Accra Metro
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <strong>Assistance Needed :</strong>
                        </td>
                        <td>
                            Water, Library, BDT Workshop,
                            Science Lab, Pavement Blocks
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
</html>
"""


def test_parse_detail_page_extracts_identity_and_badges() -> None:
    detail = parse_detail_page(
        DETAIL_HTML,
        source_detail_id="1109",
    )

    assert detail.source_detail_id == "1109"

    assert detail.displayed_school_id == "3959"

    assert detail.displayed_name == "1 SIGNAL REGIMENT BASIC"

    assert detail.ownership_raw == "Public"

    assert detail.gender_raw == "Mixed"

    assert detail.levels_raw == [
        "Primary",
        "Junior High School",
    ]

    assert detail.region_raw == "Greater Accra Region"


def test_parse_detail_page_extracts_table_fields() -> None:
    detail = parse_detail_page(
        DETAIL_HTML,
        source_detail_id="1109",
    )

    assert detail.head_name_raw == "Mr. Awuku Larbi"

    assert detail.phone_raw == "0302773029 or 0244826894"

    assert detail.location_raw == "Burma Camp, Accra"

    assert detail.postal_address_raw == "P. O. Box 251"

    assert detail.email_raw == "N/A"

    assert detail.district_raw == "Accra Metro"

    assert detail.assistance_needed_raw == (
        "Water, Library, BDT Workshop, Science Lab, Pavement Blocks"
    )


def test_parse_detail_page_allows_missing_optional_fields() -> None:
    html = """
    <html>
        <body>
            <div>
                <h4 class="detail_title">
                    <span class="label label-danger">
                        123
                    </span>

                    <b>
                        TEST SCHOOL
                    </b>
                </h4>

                <span class="label label-success">
                    Public
                </span>

                <span class="label label-success regl">
                    Ashanti Region
                </span>

                <table class="table table-user-information">
                    <tbody>
                        <tr>
                            <td>
                                <strong>District :</strong>
                            </td>
                            <td>
                                Kumasi Metro
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
    </html>
    """

    detail = parse_detail_page(
        html,
        source_detail_id="999",
    )

    assert detail.displayed_school_id == "123"

    assert detail.displayed_name == "TEST SCHOOL"

    assert detail.phone_raw is None
    assert detail.email_raw is None

    assert detail.district_raw == "Kumasi Metro"

    assert detail.levels_raw == []


def test_parse_detail_page_normalizes_label_spacing() -> None:
    html = """
    <html>
        <body>
            <table class="table table-user-information">
                <tr>
                    <td>
                        <strong>
                            Postal Address    :
                        </strong>
                    </td>

                    <td>
                        P. O. Box 123
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

    detail = parse_detail_page(
        html,
        source_detail_id="123",
    )

    assert detail.postal_address_raw == "P. O. Box 123"
