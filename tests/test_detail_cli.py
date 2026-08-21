from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from schoolminer.cli import app
from schoolminer.models.detail_acquisition import DetailAcquisitionResult

runner = CliRunner()


def test_scrape_details_invokes_detail_acquisition(
    monkeypatch,
) -> None:
    captured = {}

    crawl = SimpleNamespace(
        crawl_id="test-crawl",
        category="Junior High School",
        region_filter="All",
    )

    monkeypatch.setattr(
        "schoolminer.cli.get_crawl_job",
        lambda path, crawl_id: crawl,
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

    def fake_build_client(
        *,
        verify: bool,
    ):
        captured["verify"] = verify

        return FakeClient()

    monkeypatch.setattr(
        "schoolminer.cli.build_client",
        fake_build_client,
    )

    def fake_run_detail_acquisition(
        client,
        **kwargs,
    ):
        captured.update(kwargs)

        kwargs["on_detail_completed"](
            "1109",
            1,
            193,
        )

        return DetailAcquisitionResult(
            crawl_id="test-crawl",
            candidates_total=193,
            completed_this_run=10,
            completed_total=10,
            remaining_total=183,
        )

    monkeypatch.setattr(
        "schoolminer.cli.run_detail_acquisition",
        fake_run_detail_acquisition,
    )

    result = runner.invoke(
        app,
        [
            "scrape-details",
            "--crawl",
            "test-crawl",
            "--limit",
            "10",
            "--delay",
            "0",
            "--insecure",
        ],
    )

    assert result.exit_code == 0

    assert captured["crawl_id"] == "test-crawl"

    assert captured["limit"] == 10

    assert captured["delay_seconds"] == 0

    assert captured["verify"] is False

    assert "✓ 1109 — 1/193" in result.stdout

    assert "Candidates: 193" in result.stdout

    assert "Completed this run: 10" in result.stdout

    assert "Remaining: 183" in result.stdout


def test_scrape_details_rejects_unknown_crawl(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "schoolminer.cli.get_crawl_job",
        lambda path, crawl_id: None,
    )

    result = runner.invoke(
        app,
        [
            "scrape-details",
            "--crawl",
            "missing-crawl",
        ],
    )

    assert result.exit_code != 0

    output = result.output

    assert "Unknown crawl ID" in output
