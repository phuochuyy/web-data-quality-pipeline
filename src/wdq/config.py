"""Central settings. Every value can be overridden with an environment variable."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("WDQ_DATA_DIR", "data")))
    reports_dir: Path = field(default_factory=lambda: Path(os.getenv("WDQ_REPORTS_DIR", "reports")))
    user_agent: str = os.getenv(
        "WDQ_USER_AGENT",
        "wdq-portfolio-bot/0.1 (educational scraping practice)",
    )
    # minimum seconds between two requests to the same host
    min_interval: float = _env_float("WDQ_MIN_INTERVAL", 1.0)
    timeout: float = _env_float("WDQ_TIMEOUT", 15.0)
    max_retries: int = _env_int("WDQ_MAX_RETRIES", 3)
    books_pages: int = _env_int("WDQ_BOOKS_PAGES", 5)
    quotes_pages: int = _env_int("WDQ_QUOTES_PAGES", 5)
    # also fetch every book's own page (UPC, category, stock) for cross-source checks
    book_details: bool = os.getenv("WDQ_BOOK_DETAILS", "1") != "0"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def warehouse_path(self) -> Path:
        return self.data_dir / "warehouse.duckdb"


def setup_logging(level: str | None = None) -> None:
    """Log to stderr in a grep-friendly format."""
    logging.basicConfig(
        level=(level or os.getenv("WDQ_LOG_LEVEL", "INFO")).upper(),
        format="%(asctime)s %(levelname)-7s %(name)s - %(message)s",
        stream=sys.stderr,
        force=True,
    )
