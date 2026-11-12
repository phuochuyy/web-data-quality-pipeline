"""Build a Markdown + HTML data quality report from the warehouse."""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from wdq.quality import CheckResult, overall_status

log = logging.getLogger(__name__)

ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}


def collect_stats(con: duckdb.DuckDBPyConnection) -> dict:
    q = lambda sql: con.execute(sql).fetchall()
    return {
        "runs": q("SELECT run_id, source, row_count, loaded_at FROM pipeline_runs ORDER BY run_id DESC, source LIMIT 10"),
        "books": q("""SELECT count(*), round(avg(price_gbp), 2), min(price_gbp), max(price_gbp),
                             round(avg(in_stock::INT) * 100, 1) FROM stg_books"""),
        "ratings": q("SELECT rating, count(*) FROM stg_books GROUP BY rating ORDER BY rating"),
        "categories": q("""SELECT category, count(*) AS n, sum(stock_count), round(avg(price_gbp), 2)
                           FROM stg_books WHERE category IS NOT NULL
                           GROUP BY category ORDER BY n DESC, category LIMIT 5"""),
        "authors": q("SELECT author, count(*) AS n FROM stg_quotes GROUP BY author ORDER BY n DESC, author LIMIT 5"),
        "tags": q("SELECT tag, count(*) AS n FROM (SELECT unnest(tags) AS tag FROM stg_quotes) "
                  "GROUP BY tag ORDER BY n DESC, tag LIMIT 5"),
    }


def _md_table(headers: list[str], rows: list) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |" for row in rows]
    return "\n".join(lines)


def render_markdown(results: list[CheckResult], stats: dict, generated_at: datetime) -> str:
    status = overall_status(results)
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "WARN", "FAIL")}
    books = stats["books"][0] if stats["books"] else (0, None, None, None, None)
    parts = [
        "# Web Data Quality Report",
        (f"Generated: {generated_at:%Y-%m-%d %H:%M} UTC · Overall: **{ICON[status]} {status}** · "
        f"{counts['PASS']} pass / {counts['WARN']} warn / {counts['FAIL']} fail"),
        "## Quality checks",
        _md_table(["Status", "Table", "Check", "Dimension", "Observed", "Expected"],
                  [(f"{ICON[r.status]} {r.status}", r.table, r.check, r.dimension, r.observed, r.expected)
                   for r in results]),
        "## Latest data",
        (f"- Books: **{books[0]}** unique titles, avg price £{books[1]} (min £{books[2]}, max £{books[3]}), "
        f"{books[4]}% in stock"),
        "### Books by rating",
        _md_table(["Rating", "Books"], stats["ratings"]),
        "### Top categories (books)",
        _md_table(["Category", "Books", "Units in stock", "Avg price £"], stats["categories"]),
        "### Top authors (quotes)",
        _md_table(["Author", "Quotes"], stats["authors"]),
        "### Top tags (quotes)",
        _md_table(["Tag", "Quotes"], stats["tags"]),
        "## Recent loads",
        _md_table(["Run", "Source", "Rows", "Loaded at (UTC)"],
                  [(r[0], r[1], r[2], f"{r[3]:%Y-%m-%d %H:%M}") for r in stats["runs"]]),
    ]
    return "\n\n".join(parts) + "\n"


def _html_table(headers: list[str], rows: list, status_col: int | None = None) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        cls = f' class="{str(row[status_col]).split()[-1].lower()}"' if status_col is not None else ""
        body.append(f"<tr{cls}>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


CSS = """
body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1f2328;background:#fff}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem;font-size:.9rem}
th,td{border:1px solid #d0d7de;padding:.35rem .6rem;text-align:left}th{background:#f6f8fa}
tr.pass td:first-child{color:#1a7f37}tr.warn td:first-child{color:#9a6700}tr.fail td:first-child{color:#cf222e}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:1rem;font-weight:600;color:#fff}
.PASS{background:#1a7f37}.WARN{background:#9a6700}.FAIL{background:#cf222e}
"""


def render_html(results: list[CheckResult], stats: dict, generated_at: datetime) -> str:
    status = overall_status(results)
    books = stats["books"][0] if stats["books"] else (0, None, None, None, None)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Web Data Quality Report</title>
<style>{CSS}</style></head><body>
<h1>Web Data Quality Report</h1>
<p>Generated {generated_at:%Y-%m-%d %H:%M} UTC · <span class="badge {status}">{status}</span></p>
<h2>Quality checks</h2>
{_html_table(["Status", "Table", "Check", "Dimension", "Observed", "Expected"],
             [(r.status, r.table, r.check, r.dimension, r.observed, r.expected) for r in results], status_col=0)}
<h2>Latest data</h2>
<p>Books: <b>{books[0]}</b> unique titles, avg price £{books[1]} (min £{books[2]}, max £{books[3]}),
{books[4]}% in stock</p>
<h3>Books by rating</h3>{_html_table(["Rating", "Books"], stats["ratings"])}
<h3>Top categories (books)</h3>{_html_table(["Category", "Books", "Units in stock", "Avg price £"],
                                           stats["categories"])}
<h3>Top authors (quotes)</h3>{_html_table(["Author", "Quotes"], stats["authors"])}
<h3>Top tags (quotes)</h3>{_html_table(["Tag", "Quotes"], stats["tags"])}
<h2>Recent loads</h2>
{_html_table(["Run", "Source", "Rows", "Loaded at (UTC)"],
             [(r[0], r[1], r[2], f"{r[3]:%Y-%m-%d %H:%M}") for r in stats["runs"]])}
</body></html>
"""


def write_report(con, results: list[CheckResult], out_dir: Path, generated_at: datetime | None = None) -> dict[str, Path]:
    generated_at = generated_at or datetime.now(timezone.utc)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = collect_stats(con)
    md_path, html_path = out_dir / "report.md", out_dir / "report.html"
    md_path.write_text(render_markdown(results, stats, generated_at), encoding="utf-8")
    html_path.write_text(render_html(results, stats, generated_at), encoding="utf-8")
    log.info("report written to %s and %s", md_path, html_path)
    return {"md": md_path, "html": html_path}
