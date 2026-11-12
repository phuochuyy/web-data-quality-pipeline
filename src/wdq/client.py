"""A polite HTTP client: robots.txt, per-host rate limit, retries with backoff."""

from __future__ import annotations

import logging
import time
from typing import Callable
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)


class DisallowedByRobots(Exception):
    """Raised when robots.txt forbids fetching a URL."""


class RateLimiter:
    """Guarantees at least `min_interval` seconds between calls for the same key."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, key: str) -> float:
        """Block until the key may be used again. Returns the seconds slept."""
        now = self._clock()
        last = self._last.get(key)
        waited = 0.0
        if last is not None:
            waited = max(0.0, self.min_interval - (now - last))
            if waited:
                self._sleep(waited)
        self._last[key] = self._clock()
        return waited


class RobotsCache:
    """Downloads and caches robots.txt once per host."""

    def __init__(self, session: requests.Session, user_agent: str, timeout: float) -> None:
        self._session = session
        self._user_agent = user_agent
        self._timeout = timeout
        self._parsers: dict[str, RobotFileParser] = {}

    def _parser_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._parsers:
            robots_url = urljoin(base, "/robots.txt")
            parser = RobotFileParser(robots_url)
            try:
                resp = self._session.get(robots_url, timeout=self._timeout)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                elif resp.status_code in (401, 403):
                    parser.disallow_all = True
                else:  # 404 etc. -> no restrictions
                    parser.allow_all = True
            except requests.RequestException as exc:
                log.warning("Could not read %s (%s); assuming allowed", robots_url, exc)
                parser.allow_all = True
            log.info("robots.txt loaded for %s", base)
            self._parsers[base] = parser
        return self._parsers[base]

    def allowed(self, url: str) -> bool:
        return self._parser_for(url).can_fetch(self._user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        delay = self._parser_for(url).crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None


class PoliteClient:
    """requests.Session wrapper used by every scraper."""

    def __init__(
        self,
        user_agent: str,
        min_interval: float = 1.0,
        timeout: float = 15.0,
        max_retries: int = 3,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        retry = Retry(
            total=max_retries,
            backoff_factor=1.0,  # 1s, 2s, 4s ...
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.timeout = timeout
        self.robots = RobotsCache(self.session, user_agent, timeout)
        self.rate_limiter = rate_limiter or RateLimiter(min_interval)

    def check_allowed(self, url: str) -> None:
        if not self.robots.allowed(url):
            raise DisallowedByRobots(url)

    def throttle(self, url: str) -> None:
        host = urlsplit(url).netloc
        delay = self.robots.crawl_delay(url)
        if delay and delay > self.rate_limiter.min_interval:
            self.rate_limiter.min_interval = delay
        self.rate_limiter.wait(host)

    def get(self, url: str) -> requests.Response:
        self.check_allowed(url)
        self.throttle(url)
        started = time.perf_counter()
        resp = self.session.get(url, timeout=self.timeout)
        log.info("GET %s -> %s (%.2fs)", url, resp.status_code, time.perf_counter() - started)
        resp.raise_for_status()
        if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding  # sites often omit charset
        return resp
