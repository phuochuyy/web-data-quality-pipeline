"""DuckDB warehouse: raw tables (append per run) + cleaned staging views."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

TABLE_COLUMNS = {
    "raw_books": ["run_id", "title", "url", "price_gbp", "rating", "availability", "in_stock",
                  "page", "source_url", "scraped_at",
                  "upc", "category", "stock_count", "detail_price_gbp", "detail_title"],
    "raw_quotes": ["run_id", "text", "author", "tags", "page", "source_url", "scraped_at"],
}

DDL = """
CREATE TABLE IF NOT EXISTS raw_books (
    run_id VARCHAR, title VARCHAR, url VARCHAR, price_gbp DOUBLE, rating INTEGER,
    availability VARCHAR, in_stock BOOLEAN, page INTEGER, source_url VARCHAR, scraped_at TIMESTAMP
);
-- detail-page columns, added in place so a warehouse from an older run keeps working
ALTER TABLE raw_books ADD COLUMN IF NOT EXISTS upc VARCHAR;
ALTER TABLE raw_books ADD COLUMN IF NOT EXISTS category VARCHAR;
ALTER TABLE raw_books ADD COLUMN IF NOT EXISTS stock_count INTEGER;
ALTER TABLE raw_books ADD COLUMN IF NOT EXISTS detail_price_gbp DOUBLE;
ALTER TABLE raw_books ADD COLUMN IF NOT EXISTS detail_title VARCHAR;
CREATE TABLE IF NOT EXISTS raw_quotes (
    run_id VARCHAR, text VARCHAR, author VARCHAR, tags VARCHAR[], page INTEGER,
    source_url VARCHAR, scraped_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR, source VARCHAR, row_count INTEGER, loaded_at TIMESTAMP,
    PRIMARY KEY (run_id, source)
);

-- Silver layer: latest run only, trimmed and de-duplicated
CREATE OR REPLACE VIEW stg_books AS
SELECT DISTINCT ON (url)
    trim(title) AS title, url, upc, category, price_gbp, rating, in_stock, stock_count, scraped_at, run_id
FROM raw_books
WHERE run_id = (SELECT max(run_id) FROM raw_books)
ORDER BY url;

CREATE OR REPLACE VIEW stg_quotes AS
SELECT DISTINCT ON (text, author)
    trim(text) AS text, trim(author) AS author, tags, scraped_at, run_id
FROM raw_quotes
WHERE run_id = (SELECT max(run_id) FROM raw_quotes)
ORDER BY text, author;
"""

SOURCE_TABLE = {"books": "raw_books", "quotes": "raw_quotes"}


def connect(path: Path | str) -> duckdb.DuckDBPyConnection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(DDL)
    return con


def load_parquet(con: duckdb.DuckDBPyConnection, source: str, run_id: str, parquet_path: Path) -> int:
    """Idempotent load of one run: re-running the same run_id replaces its rows."""
    table = SOURCE_TABLE[source]
    cols = TABLE_COLUMNS[table]
    path_sql = Path(parquet_path).as_posix().replace("'", "''")
    available = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path_sql}')").fetchall()}
    select = ", ".join(c if c in available else f"NULL AS {c}" for c in cols)

    con.execute("BEGIN")
    try:
        con.execute(f"DELETE FROM {table} WHERE run_id = ?", [run_id])
        if len(available) > 1:  # an empty scrape only has the run_id column
            con.execute(f"INSERT INTO {table} ({', '.join(cols)}) SELECT {select} FROM read_parquet('{path_sql}')")
        rows = con.execute(f"SELECT count(*) FROM {table} WHERE run_id = ?", [run_id]).fetchone()[0]
        con.execute("DELETE FROM pipeline_runs WHERE run_id = ? AND source = ?", [run_id, source])
        con.execute(
            "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)",
            [run_id, source, rows, datetime.now(timezone.utc).replace(tzinfo=None)],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    log.info("loaded %d rows into %s (run %s)", rows, table, run_id)
    return rows
