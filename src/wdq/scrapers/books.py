"""Static site: https://books.toscrape.com (Requests + BeautifulSoup)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from wdq.client import DisallowedByRobots, PoliteClient

log = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
_PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")


def parse_price(text: str) -> float | None:
    match = _PRICE_RE.search(text or "")
    return float(match.group(1)) if match else None


def parse_listing(html: str, page_url: str) -> tuple[list[dict], str | None]:
    """Parse one catalogue page. Returns (records, next_page_url)."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for pod in soup.select("article.product_pod"):
        link = pod.select_one("h3 a")
        rating_el = pod.select_one("p.star-rating")
        rating_word = next((c for c in (rating_el.get("class", []) if rating_el else []) if c in RATINGS), None)
        availability = pod.select_one("p.availability")
        availability_text = availability.get_text(strip=True) if availability else None
        records.append(
            {
                "title": link.get("title") if link else None,
                "url": urljoin(page_url, link["href"]) if link and link.get("href") else None,
                "price_gbp": parse_price(pod.select_one("p.price_color").get_text())
                if pod.select_one("p.price_color")
                else None,
                "rating": RATINGS.get(rating_word) if rating_word else None,
                "availability": availability_text,
                "in_stock": bool(availability_text and "in stock" in availability_text.lower()),
            }
        )
    nxt = soup.select_one("li.next a")
    next_url = urljoin(page_url, nxt["href"]) if nxt and nxt.get("href") else None
    return records, next_url


_STOCK_RE = re.compile(r"\((\d+) available\)")
DETAIL_FIELDS = ("upc", "category", "stock_count", "detail_price_gbp", "detail_title")


def parse_detail(html: str) -> dict:
    """Parse a book's own page: fields the listing does not have, plus the price and
    title again so the two sources can be cross-checked."""
    soup = BeautifulSoup(html, "html.parser")
    table = {tr.th.get_text(strip=True): tr.td.get_text(strip=True)
             for tr in soup.select("table.table tr") if tr.th and tr.td}
    crumbs = [li.get_text(strip=True) for li in soup.select("ul.breadcrumb li")]
    main = soup.select_one("div.product_main")
    price = main.select_one("p.price_color") if main else None
    title = main.select_one("h1") if main else None
    stock = _STOCK_RE.search(table.get("Availability", ""))
    return {
        "upc": table.get("UPC") or None,
        "category": crumbs[2] if len(crumbs) > 3 else None,  # Home > Books > <category> > <title>
        "stock_count": int(stock.group(1)) if stock else (0 if "Availability" in table else None),
        "detail_price_gbp": parse_price(price.get_text()) if price else None,
        "detail_title": title.get_text(strip=True) if title else None,
    }


def scrape_books(client: PoliteClient, max_pages: int = 5, start_url: str = BASE_URL,
                 details: bool = True) -> list[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    url: str | None = start_url
    records: list[dict] = []
    page = 0
    while url and page < max_pages:
        page += 1
        resp = client.get(url)
        page_records, url = parse_listing(resp.text, resp.url)
        for rec in page_records:
            rec.update(page=page, source_url=resp.url, scraped_at=scraped_at)
        records.extend(page_records)
        log.info("books page %d: %d records", page, len(page_records))
    log.info("books: %d records from %d pages", len(records), page)

    if details:
        failed = 0
        for i, rec in enumerate(records, 1):
            try:
                rec.update(parse_detail(client.get(rec["url"]).text))
            except (requests.RequestException, DisallowedByRobots) as exc:  # keep the row; checks report the gap
                failed += 1
                rec.update(dict.fromkeys(DETAIL_FIELDS))
                log.warning("detail page failed for %s: %s", rec["url"], exc)
            if i % 20 == 0:
                log.info("book details: %d/%d", i, len(records))
        log.info("book details: %d fetched, %d failed", len(records) - failed, failed)
    return records
