"""Raw landing zone: data/raw/<source>/dt=YYYY-MM-DD/<run_id>.{json,parquet}."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def new_run_id(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


def write_raw(records: list[dict], source: str, run_id: str, raw_dir: Path) -> dict[str, Path]:
    """Write records untouched as JSON (source of truth) and as Parquet (fast to load)."""
    day = f"{run_id[0:4]}-{run_id[4:6]}-{run_id[6:8]}"
    out_dir = Path(raw_dir) / source / f"dt={day}"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{run_id}.json"
    payload = {"source": source, "run_id": run_id, "count": len(records), "records": records}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    parquet_path = out_dir / f"{run_id}.parquet"
    df = pd.DataFrame.from_records(records)
    df.insert(0, "run_id", run_id)
    if "scraped_at" in df:
        # typed, timezone-naive UTC timestamp -> loads cleanly into DuckDB TIMESTAMP
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True).dt.tz_localize(None)
    df.to_parquet(parquet_path, index=False)

    log.info("raw %s: %d records -> %s", source, len(records), out_dir)
    return {"json": json_path, "parquet": parquet_path}
