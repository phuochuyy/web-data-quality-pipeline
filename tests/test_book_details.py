from datetime import datetime

import duckdb
import requests

from wdq import quality, warehouse
from wdq.scrapers.books import parse_detail, scrape_books
from wdq.storage import write_raw

NOW = datetime(2026, 1, 2, 12, 0)
RUN = "20260102T120000Z"


def test_parse_detail(detail_html):
    d = parse_detail(detail_html)
    assert d == {"upc": "a897fe39b1053632", "category": "Poetry", "stock_count": 22,
                 "detail_price_gbp": 51.77, "detail_title": "A Light in the Attic"}


def test_parse_detail_out_of_stock(detail_html):
    html = detail_html.replace("In stock (22 available)", "Out of stock")
    assert parse_detail(html)["stock_count"] == 0


class FakeResponse:
    def __init__(self, text, url):
        self.text, self.url = text, url


class FakeClient:
    """Serves one listing page and the detail pages; one detail page fails."""

    def __init__(self, listing_html, detail_html):
        self.listing_html, self.detail_html = listing_html, detail_html

    def get(self, url):
        if url.endswith("page-1.html"):
            return FakeResponse(self.listing_html.replace('href="page-2.html"', ""), url)
        if "tipping-the-velvet" in url:
            raise requests.ConnectionError("boom")
        return FakeResponse(self.detail_html, url)


def test_scrape_books_keeps_rows_when_a_detail_page_fails(books_html, detail_html):
    records = scrape_books(FakeClient(books_html, detail_html), max_pages=1)
    assert len(records) == 2
    assert records[0]["upc"] == "a897fe39b1053632"
    assert records[1]["upc"] is None and records[1]["title"] == "Tipping the Velvet"


def book(i, **overrides):
    rec = {"title": f"Book {i}", "url": f"https://x/{i}", "price_gbp": 10.0 + i, "rating": 3,
           "availability": "In stock", "in_stock": True, "page": 1, "source_url": "https://x",
           "scraped_at": NOW.isoformat(), "upc": f"upc{i}", "category": "Poetry", "stock_count": 5,
           "detail_price_gbp": 10.0 + i, "detail_title": f"Book {i}"}
    rec.update(overrides)
    return rec


def load_books(tmp_path, records):
    con = warehouse.connect(":memory:")
    paths = write_raw(records, "books", RUN, tmp_path)
    warehouse.load_parquet(con, "books", RUN, paths["parquet"])
    return con


def by_check(con):
    return {r.check: r for r in quality.run_checks(con, now=NOW) if r.table == "raw_books"}


def test_consistent_details_pass(tmp_path):
    results = by_check(load_books(tmp_path, [book(i) for i in range(25)]))
    for name in ("one_upc_per_url", "price_listing_eq_detail", "title_listing_eq_detail",
                 "in_stock_matches_stock_count", "stock_count_non_negative", "not_null:upc"):
        assert results[name].status == quality.PASS, results[name]


def test_inconsistencies_are_detected(tmp_path):
    rows = [book(i) for i in range(25)]
    rows[0]["detail_price_gbp"] = 99.0             # listing and detail disagree
    rows[1]["detail_title"] = "Another title"
    rows[2]["stock_count"] = 0                       # says in stock, but 0 units
    rows[3]["upc"] = rows[4]["upc"]                  # two pages share one UPC
    results = by_check(load_books(tmp_path, rows))
    assert results["price_listing_eq_detail"].status == quality.FAIL
    assert results["title_listing_eq_detail"].status == quality.FAIL
    assert results["in_stock_matches_stock_count"].status == quality.FAIL
    assert results["one_upc_per_url"].status == quality.FAIL


def test_detail_checks_skipped_without_details(tmp_path):
    rows = [book(i, upc=None, category=None, stock_count=None, detail_price_gbp=None, detail_title=None)
            for i in range(25)]
    results = by_check(load_books(tmp_path, rows))
    assert "price_listing_eq_detail" not in results
    assert results["row_count"].status == quality.PASS


def test_warehouse_from_older_version_is_migrated(tmp_path):
    db = tmp_path / "old.duckdb"
    old = duckdb.connect(str(db))
    old.execute("""CREATE TABLE raw_books (run_id VARCHAR, title VARCHAR, url VARCHAR, price_gbp DOUBLE,
                   rating INTEGER, availability VARCHAR, in_stock BOOLEAN, page INTEGER,
                   source_url VARCHAR, scraped_at TIMESTAMP)""")
    old.close()
    con = warehouse.connect(db)
    paths = write_raw([book(i) for i in range(3)], "books", RUN, tmp_path)
    assert warehouse.load_parquet(con, "books", RUN, paths["parquet"]) == 3
    assert con.execute("SELECT count(upc) FROM raw_books").fetchone()[0] == 3


def test_placeholder_categories_are_cleaned_and_tracked(tmp_path):
    rows = [book(i) for i in range(25)]
    rows[0]["category"] = "Add a comment"
    rows[1]["category"] = "Default"
    con = load_books(tmp_path, rows)
    result = by_check(con)["placeholder_category_share"]
    assert result.status == quality.PASS                    # 2 of 25 = 8% <= 20%
    assert result.observed.startswith("2 (8%)")
    cats = dict(con.execute("SELECT category, count(*) FROM stg_books GROUP BY 1").fetchall())
    assert cats["Uncategorized"] == 2 and "Default" not in cats
    assert con.execute("SELECT count(*) FROM raw_books WHERE category = 'Default'").fetchone()[0] == 1


def test_many_placeholder_categories_warn(tmp_path):
    rows = [book(i, category="Default" if i < 10 else "Poetry") for i in range(25)]
    assert by_check(load_books(tmp_path, rows))["placeholder_category_share"].status == quality.WARN
