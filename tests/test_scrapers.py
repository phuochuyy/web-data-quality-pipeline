from wdq.scrapers.books import parse_listing, parse_price
from wdq.scrapers.quotes_js import parse_quotes

PAGE = "https://books.toscrape.com/catalogue/page-1.html"


def test_parse_books_listing(books_html):
    records, next_url = parse_listing(books_html, PAGE)
    assert len(records) == 2
    first = records[0]
    assert first["title"] == "A Light in the Attic"
    assert first["url"] == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert first["price_gbp"] == 51.77
    assert first["rating"] == 3
    assert first["in_stock"] is True
    assert records[1]["in_stock"] is False
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


def test_parse_price_handles_mojibake():
    # "Â£" appears when a page is decoded with the wrong charset
    assert parse_price("Â£53.74") == 53.74
    assert parse_price("") is None


def test_parse_quotes(quotes_html):
    records, next_url = parse_quotes(quotes_html, "https://quotes.toscrape.com/js/")
    assert [r["author"] for r in records] == ["Albert Einstein", "Steve Martin"]
    assert records[0]["text"].startswith("The world")
    assert not records[0]["text"].endswith("”")
    assert records[0]["tags"] == ["change", "thinking"]
    assert records[1]["tags"] == []
    assert next_url == "https://quotes.toscrape.com/js/page/2/"


def test_last_page_has_no_next():
    records, next_url = parse_quotes("<html></html>", "https://quotes.toscrape.com/js/page/10/")
    assert records == [] and next_url is None
