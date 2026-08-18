import json
from datetime import datetime, timezone

from schoolminer.models.raw import RawDirectoryRecord
from schoolminer.storage.raw_store import append_raw_record


def build_raw_record(
    *,
    source_detail_id: str = "1109",
    position: int = 1,
) -> RawDirectoryRecord:
    return RawDirectoryRecord(
        crawl_id="test-crawl-123",
        source="ghana_education_directory",
        category="Junior High School",
        region_filter="All",
        page=1,
        position=position,
        fetched_at=datetime(
            2026,
            8,
            18,
            1,
            20,
            tzinfo=timezone.utc,
        ),
        source_detail_id=source_detail_id,
        source_url=("https://ghanaeducationdirectory.com/search/searchs"),
        detail_url=(f"https://ghanaeducationdirectory.com/Search/Details/{source_detail_id}"),
        raw={
            "InstitutionName": ("1 SIGNAL REGIMENT BASIC"),
            "InstitutionId": 1109,
            "TownName": "Burma Camp, Accra",
            "Region": "Greater Accra Region",
            "Phone": ("0302773029 or 0244826894"),
            "OwnerShipId": 2,
            "Logo": (
                "https://saghedu.blob.core.windows.net/ghedu/institutions/images/1109_ico.png"
            ),
        },
    )


def test_raw_record_preserves_source_payload() -> None:
    record = build_raw_record()

    payload = json.loads(record.model_dump_json())

    assert payload["source_detail_id"] == "1109"

    assert payload["raw"]["InstitutionId"] == 1109

    assert payload["raw"]["Phone"] == "0302773029 or 0244826894"

    assert payload["raw"]["InstitutionName"] == "1 SIGNAL REGIMENT BASIC"


def test_append_raw_record_writes_jsonl(
    tmp_path,
) -> None:
    output_path = tmp_path / "crawl" / "records.jsonl"

    record = build_raw_record()

    append_raw_record(
        output_path,
        record,
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    payload = json.loads(lines[0])

    assert payload["source_detail_id"] == "1109"

    assert payload["raw"]["InstitutionName"] == "1 SIGNAL REGIMENT BASIC"


def test_append_raw_record_preserves_existing_lines(
    tmp_path,
) -> None:
    output_path = tmp_path / "records.jsonl"

    first_record = build_raw_record(
        source_detail_id="1109",
        position=1,
    )

    second_record = build_raw_record(
        source_detail_id="9543",
        position=2,
    )

    append_raw_record(
        output_path,
        first_record,
    )

    append_raw_record(
        output_path,
        second_record,
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2

    first_payload = json.loads(lines[0])

    second_payload = json.loads(lines[1])

    assert first_payload["source_detail_id"] == "1109"

    assert second_payload["source_detail_id"] == "9543"
