"""
etl/load/load_events.py
--------------------------
Loads event_statsbomb from data/transformed/events_statsbomb.csv
into PostgreSQL.

Strategy: TRUNCATE … CASCADE then INSERT via pandas to_sql.

The events table can be large (tens of thousands of rows per match),
so we use a larger chunksize and log progress every 10k rows.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.load.db import get_engine

logger = logging.getLogger(__name__)

TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"
CSV_PATH = TRANSFORMED_DIR / "events_statsbomb.csv"
TABLE_NAME = "event_statsbomb"

# Columns present in the DB schema (matches schema.sql)
_DB_COLS = ["event_id", "match_id", "player_id", "event_type", "period", "minute", "second", "x", "y", "end_x", "end_y", "outcome", "xg"]
_INT_COLS = ["player_id", "period", "minute", "second"]
_FLOAT_COLS = ["x", "y", "end_x", "end_y", "xg"]


def load() -> int:
    """TRUNCATE event_statsbomb and reload from CSV. Returns row count."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Transformed CSV not found: {CSV_PATH}. "
            "Run `python -m etl.transform.run_transform` first."
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8", low_memory=False)
    logger.info("Read %d event rows from %s", len(df), CSV_PATH)

    # Only keep columns that exist in the DB schema
    keep = [c for c in _DB_COLS if c in df.columns]
    df = df[keep].copy()

    for col in _INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in _FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} CASCADE"))
        logger.info("TRUNCATED %s", TABLE_NAME)

    # Insert in chunks with progress logging
    chunk_size = 2000
    total = len(df)
    inserted = 0
    for start in range(0, total, chunk_size):
        chunk = df.iloc[start : start + chunk_size]
        chunk.to_sql(
            TABLE_NAME,
            engine,
            if_exists="append",
            index=False,
            method="multi",
        )
        inserted += len(chunk)
        if inserted % 10000 < chunk_size or inserted >= total:
            logger.info("  Inserted %d / %d rows into %s", inserted, total, TABLE_NAME)

    logger.info("Loaded %d rows into %s", total, TABLE_NAME)
    return total


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    load()


if __name__ == "__main__":
    main()
