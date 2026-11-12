"""JavaScript-rendered site: https://quotes.toscrape.com/js/ (Playwright).

Playwright only renders the page; parsing is plain BeautifulSoup so it can be
unit-tested without a browser. robots.txt and the rate limit are enforced by the
same PoliteClient used for the static scraper.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from wdq.client import PoliteClient

log = logging.getLogger(__name__)

BASE_URL = "https://quotes.toscrape.com/js/"


def parse_quotes(html: str, page_url: str) -> tuple[list[dict], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for q in soup.select("div.quote"):
        text = q.select_one("span.text")
        author = q.select_one("small.author")
        records.append(
            {
                "text": text.get_text(strip=True).strip("“”\"") if text else None,
                "author": author.get_text(strip=True) if author else None,
                "tags": [t.get_text(strip=True) for t in q.select("a.tag")],
            }
        )
    nxt = soup.select_one("li.next a")
    next_url = urljoin(page_url, nxt["href"]) if nxt and nxt.get("href") else None
    return records, next_url


def scrape_quotes_js(client: PoliteClient, max_pages: int = 5, start_url: str = BASE_URL) -> list[dict]:
    from playwright.sync_api import sync_playwright  # imported lazily: heavy dependency

    scraped_at = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []
    url: str | None = start_url
    page_no = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=client.session.headers["User-Agent"])
            while url and page_no < max_pages:
                page_no += 1
                client.check_allowed(url)
                client.throttle(url)
                page.goto(url, timeout=client.timeout * 1000)
                page.wait_for_selector("div.quote", timeout=client.timeout * 1000)
                page_records, url = parse_quotes(page.content(), page.url)
                for rec in page_records:
                    rec.update(page=page_no, source_url=page.url, scraped_at=scraped_at)
                records.extend(page_records)
                log.info("quotes page %d: %d records", page_no, len(page_records))
        finally:
            browser.close()
    log.info("quotes: %d records from %d pages", len(records), page_no)
    return records
