import json

from schoolminer.storage.processed_store import (
    processed_crawl_dir,
    processed_schools_path,
    write_candidate_jsonl,
)


def test_processed_schools_path(
    tmp_path,
) -> None:
    path = processed_schools_path(
        tmp_path,
        "test-crawl",
    )

    assert path == (
        tmp_path
        / "processed"
        / "crawls"
        / "test-crawl"
        / "schools.jsonl"
    )


