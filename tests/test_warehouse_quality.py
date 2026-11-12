from datetime import datetime, timedelta, timezone

import pytest

from wdq import quality, warehouse
from wdq.storage import write_raw

NOW = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)


def book(i, **overrides):
    rec = {
        "title": f"Book {i}", "url": f"https://x/{i}", "price_gbp": 10.0 + i % 40, "rating": 1 + i % 5,
        "availability": "In stock", "in_stock": True, "page": 1, "source_url": "https://x",
        "scraped_at": NOW.isoformat(),
    }
    rec.update(overrides)
    return rec


def quote(i):
    return {"text": f"Quote {i}", "author": f"Author {i % 3}", "tags": ["a"], "page": 1,
            "source_url": "https://q", "scraped_at": NOW.isoformat()}


@pytest.fixture
def con():
    c = warehouse.connect(":memory:")
    yield c
    c.close()


def load(con, tmp_path, source, records, run_id):
    paths = write_raw(records, source, run_id, tmp_path)
    return warehouse.load_parquet(con, source, run_id, paths["parquet"])


def by_check(results):
    return {(r.table, r.check): r for r in results}


def test_raw_files_written(tmp_path):
    paths = write_raw([book(1)], "books", "20260102T120000Z", tmp_path)
    assert paths["json"].exists() and paths["parquet"].exists()
    assert "dt=2026-01-02" in str(paths["json"])


def test_load_is_idempotent(con, tmp_path):
    rows = [book(i) for i in range(30)]
    assert load(con, tmp_path, "books", rows, "20260102T120000Z") == 30
    assert load(con, tmp_path, "books", rows, "20260102T120000Z") == 30
    assert con.execute("SELECT count(*) FROM raw_books").fetchone()[0] == 30


def test_clean_data_passes(con, tmp_path):
    load(con, tmp_path, "books", [book(i) for i in range(30)], "20260102T120000Z")
    load(con, tmp_path, "quotes", [quote(i) for i in range(12)], "20260102T120000Z")
    results = quality.run_checks(con, now=NOW.replace(tzinfo=None) + timedelta(hours=1))
    assert quality.overall_status(results) == quality.PASS, [r for r in results if r.status != "PASS"]


def test_problems_are_detected(con, tmp_path):
    rows = [book(i) for i in range(30)]
    rows[0]["title"] = None          # completeness
    rows[1]["price_gbp"] = -5.0      # validity
    rows[2]["rating"] = 9            # validity
    rows.append(dict(rows[3]))       # duplicate url
    load(con, tmp_path, "books", rows, "20260102T120000Z")
    results = by_check(quality.run_checks(con, now=NOW.replace(tzinfo=None) + timedelta(days=3)))

    assert results[("raw_books", "not_null:title")].status == quality.FAIL
    assert results[("raw_books", "price_positive")].status == quality.FAIL
    assert results[("raw_books", "rating_1_to_5")].status == quality.FAIL
    assert results[("raw_books", "unique:url")].status == quality.WARN
    assert results[("raw_books", "freshness")].status == quality.FAIL      # 3 days old
    assert results[("raw_quotes", "row_count")].status == quality.FAIL     # never loaded


def test_volume_drop_is_flagged(con, tmp_path):
    for day in range(1, 4):
        load(con, tmp_path, "books", [book(i) for i in range(100)], f"2026010{day}T120000Z")
    load(con, tmp_path, "books", [book(i) for i in range(40)], "20260104T120000Z")
    result = by_check(quality.run_checks(con, now=NOW.replace(tzinfo=None)))[("raw_books", "row_count_vs_history")]
    assert result.status == quality.WARN
    assert "-60%" in result.observed


def test_staging_view_deduplicates(con, tmp_path):
    rows = [book(i) for i in range(25)] + [book(0)]
    load(con, tmp_path, "books", rows, "20260102T120000Z")
    assert con.execute("SELECT count(*) FROM stg_books").fetchone()[0] == 25
