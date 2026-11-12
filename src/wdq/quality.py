"""Data quality checks written in plain SQL on top of DuckDB.

Every check returns a CheckResult with status PASS / WARN / FAIL. A FAIL makes
the CLI exit non-zero so the scheduled GitHub Actions run turns red.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import duckdb

log = logging.getLogger(__name__)

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class CheckResult:
    table: str
    check: str
    dimension: str  # completeness | uniqueness | validity | freshness | anomaly | volume
    status: str
    observed: str
    expected: str

    def as_dict(self) -> dict:
        return asdict(self)


def _latest_run(con, table: str) -> str | None:
    return con.execute(f"SELECT max(run_id) FROM {table}").fetchone()[0]


def check_row_count(con, table: str, run_id: str, min_rows: int) -> CheckResult:
    n = con.execute(f"SELECT count(*) FROM {table} WHERE run_id = ?", [run_id]).fetchone()[0]
    return CheckResult(table, "row_count", "volume", PASS if n >= min_rows else FAIL, str(n), f">= {min_rows}")


def check_not_null(con, table: str, run_id: str, column: str, warn_ratio: float = 0.0,
                   fail_ratio: float = 0.01) -> CheckResult:
    total, nulls = con.execute(
        f"""SELECT count(*), count(*) FILTER (WHERE {column} IS NULL OR CAST({column} AS VARCHAR) = '')
            FROM {table} WHERE run_id = ?""",
        [run_id],
    ).fetchone()
    ratio = nulls / total if total else 0.0
    status = FAIL if ratio > fail_ratio else WARN if ratio > warn_ratio else PASS
    return CheckResult(table, f"not_null:{column}", "completeness", status,
                       f"{nulls} missing ({ratio:.1%})", f"<= {fail_ratio:.0%} missing")


def check_unique(con, table: str, run_id: str, columns: list[str]) -> CheckResult:
    key = ", ".join(columns)
    dupes = con.execute(
        f"""SELECT coalesce(sum(c - 1), 0) FROM (
                SELECT count(*) AS c FROM {table} WHERE run_id = ? GROUP BY {key} HAVING count(*) > 1)""",
        [run_id],
    ).fetchone()[0]
    # duplicates are removed in the staging view, so they only warn
    return CheckResult(table, f"unique:{key}", "uniqueness", PASS if dupes == 0 else WARN,
                       f"{dupes} duplicate rows", "0")


def check_condition(con, table: str, run_id: str, name: str, bad_rows_sql: str, expected: str) -> CheckResult:
    bad = con.execute(f"SELECT count(*) FROM {table} WHERE run_id = ? AND ({bad_rows_sql})", [run_id]).fetchone()[0]
    return CheckResult(table, name, "validity", PASS if bad == 0 else FAIL, f"{bad} invalid rows", expected)


def check_freshness(con, table: str, max_age: timedelta, now: datetime) -> CheckResult:
    latest = con.execute(f"SELECT max(scraped_at) FROM {table}").fetchone()[0]
    expected = f"< {max_age.total_seconds() / 3600:g}h old"
    if latest is None:
        return CheckResult(table, "freshness", "freshness", FAIL, "no data", expected)
    age = now - latest
    status = PASS if age <= max_age else FAIL
    age_text = str(age).split(".")[0]  # drop microseconds
    return CheckResult(table, "freshness", "freshness", status, f"last scrape {age_text} ago", expected)


def check_volume_anomaly(con, table: str, run_id: str, tolerance: float = 0.3, history: int = 7) -> CheckResult:
    """Compare this run's row count with the average of previous runs."""
    source = {"raw_books": "books", "raw_quotes": "quotes"}[table]
    current = con.execute("SELECT row_count FROM pipeline_runs WHERE source = ? AND run_id = ?",
                          [source, run_id]).fetchone()
    prev = con.execute(
        """SELECT avg(row_count), count(*) FROM (
               SELECT row_count FROM pipeline_runs WHERE source = ? AND run_id < ?
               ORDER BY run_id DESC LIMIT ?)""",
        [source, run_id, history],
    ).fetchone()
    if not current or not prev[1]:
        return CheckResult(table, "row_count_vs_history", "anomaly", PASS, "no history yet", f"within ±{tolerance:.0%}")
    change = (current[0] - prev[0]) / prev[0] if prev[0] else 0.0
    status = PASS if abs(change) <= tolerance else WARN
    return CheckResult(table, "row_count_vs_history", "anomaly", status,
                       f"{current[0]} vs avg {prev[0]:.0f} ({change:+.0%})", f"within ±{tolerance:.0%}")


def check_zscore_outliers(con, table: str, run_id: str, column: str, z: float = 3.0) -> CheckResult:
    outliers = con.execute(
        f"""WITH s AS (SELECT avg({column}) AS mu, stddev_samp({column}) AS sd
                       FROM {table} WHERE run_id = ?)
            SELECT count(*) FROM {table}, s
            WHERE run_id = ? AND s.sd > 0 AND abs(({column} - s.mu) / s.sd) > ?""",
        [run_id, run_id, z],
    ).fetchone()[0]
    return CheckResult(table, f"outliers:{column}", "anomaly", PASS if outliers == 0 else WARN,
                       f"{outliers} values with |z| > {z}", "0")


def run_checks(con: duckdb.DuckDBPyConnection, now: datetime | None = None,
               max_age: timedelta = timedelta(hours=26)) -> list[CheckResult]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    results: list[CheckResult] = []

    books_run = _latest_run(con, "raw_books")
    if books_run:
        results += [
            check_row_count(con, "raw_books", books_run, min_rows=20),
            *(check_not_null(con, "raw_books", books_run, c) for c in ("title", "url", "price_gbp", "rating")),
            check_unique(con, "raw_books", books_run, ["url"]),
            check_condition(con, "raw_books", books_run, "price_positive", "price_gbp <= 0", "price_gbp > 0"),
            check_condition(con, "raw_books", books_run, "rating_1_to_5", "rating NOT BETWEEN 1 AND 5", "1..5"),
            check_freshness(con, "raw_books", max_age, now),
            check_volume_anomaly(con, "raw_books", books_run),
            check_zscore_outliers(con, "raw_books", books_run, "price_gbp"),
        ]
    else:
        results.append(CheckResult("raw_books", "row_count", "volume", FAIL, "table empty", ">= 20"))

    quotes_run = _latest_run(con, "raw_quotes")
    if quotes_run:
        results += [
            check_row_count(con, "raw_quotes", quotes_run, min_rows=10),
            *(check_not_null(con, "raw_quotes", quotes_run, c) for c in ("text", "author")),
            check_unique(con, "raw_quotes", quotes_run, ["text", "author"]),
            check_freshness(con, "raw_quotes", max_age, now),
            check_volume_anomaly(con, "raw_quotes", quotes_run),
        ]
    else:
        results.append(CheckResult("raw_quotes", "row_count", "volume", FAIL, "table empty", ">= 10"))

    for r in results:
        level = logging.WARNING if r.status != PASS else logging.INFO
        log.log(level, "[%s] %s.%s observed=%s expected=%s", r.status, r.table, r.check, r.observed, r.expected)
    return results


def overall_status(results: list[CheckResult]) -> str:
    statuses = {r.status for r in results}
    return FAIL if FAIL in statuses else WARN if WARN in statuses else PASS
