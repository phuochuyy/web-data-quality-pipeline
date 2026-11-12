from datetime import datetime

from wdq import quality, warehouse
from wdq.report import write_report
from wdq.storage import write_raw


def test_report_files_contain_checks(tmp_path):
    con = warehouse.connect(":memory:")
    records = [{"title": f"B{i}", "url": f"u{i}", "price_gbp": 12.5, "rating": 4, "availability": "In stock",
                "in_stock": True, "page": 1, "source_url": "s", "scraped_at": "2026-01-02T12:00:00+00:00"}
               for i in range(25)]
    paths = write_raw(records, "books", "20260102T120000Z", tmp_path / "raw")
    warehouse.load_parquet(con, "books", "20260102T120000Z", paths["parquet"])
    results = quality.run_checks(con, now=datetime(2026, 1, 2, 13))

    out = write_report(con, results, tmp_path / "reports", generated_at=datetime(2026, 1, 2, 13))
    md = out["md"].read_text(encoding="utf-8")
    page = out["html"].read_text(encoding="utf-8")

    assert "# Web Data Quality Report" in md
    assert "not_null:title" in md and "raw_quotes" in md  # quotes missing -> FAIL row is reported
    assert "FAIL" in md
    assert page.startswith("<!doctype html>") and "<table>" in page


def test_footer_links_ci_run(monkeypatch):
    from wdq.report import _footer

    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    assert "local run" in _footer()
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "me/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    assert 'href="https://github.com/me/repo/actions/runs/42"' in _footer()
