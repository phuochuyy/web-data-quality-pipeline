"""Command line entry point: `wdq run` executes the whole pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta

from wdq import quality, warehouse
from wdq.client import PoliteClient
from wdq.config import Settings, setup_logging
from wdq.report import write_report
from wdq.scrapers.books import scrape_books
from wdq.scrapers.quotes_js import scrape_quotes_js
from wdq.storage import new_run_id, write_raw

log = logging.getLogger("wdq")


def cmd_scrape(settings: Settings, sources: list[str]) -> str:
    run_id = new_run_id()
    client = PoliteClient(settings.user_agent, settings.min_interval, settings.timeout, settings.max_retries)
    con = warehouse.connect(settings.warehouse_path)
    try:
        for source in sources:
            log.info("scraping %s (run %s)", source, run_id)
            if source == "books":
                records = scrape_books(client, settings.books_pages, details=settings.book_details)
            else:
                records = scrape_quotes_js(client, settings.quotes_pages)
            paths = write_raw(records, source, run_id, settings.raw_dir)
            warehouse.load_parquet(con, source, run_id, paths["parquet"])
    finally:
        con.close()
    return run_id


def cmd_check_and_report(settings: Settings) -> int:
    con = warehouse.connect(settings.warehouse_path)
    try:
        results = quality.run_checks(con, max_age=timedelta(hours=settings.max_age_hours))
        paths = write_report(con, results, settings.reports_dir)
    finally:
        con.close()
    status = quality.overall_status(results)
    print(f"Data quality: {status} -> {paths['md']} / {paths['html']}")
    return 1 if status == quality.FAIL else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wdq", description="Web data quality pipeline")
    parser.add_argument("--log-level", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    scrape = sub.add_parser("scrape", help="scrape sources and load them into DuckDB")
    scrape.add_argument("--source", choices=["books", "quotes"], action="append",
                        help="repeatable; default: all sources")
    sub.add_parser("check", help="run quality checks and write the report")
    run = sub.add_parser("run", help="scrape + check + report")
    run.add_argument("--source", choices=["books", "quotes"], action="append")
    args = parser.parse_args(argv)

    setup_logging(args.log_level)
    settings = Settings()
    try:
        if args.command in ("scrape", "run"):
            cmd_scrape(settings, args.source or ["books", "quotes"])
        if args.command in ("check", "run"):
            return cmd_check_and_report(settings)
        return 0
    except Exception:
        log.exception("pipeline failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
