"""
etl/load/load_fact_match.py
-----------------------------
Loads fact_match from data/transformed/fact_match.csv into PostgreSQL.

Strategy: TRUNCATE … CASCADE then INSERT via pandas to_sql.
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
CSV_PATH = TRANSFORMED_DIR / "fact_match.csv"
TABLE_NAME = "fact_match"


def load() -> int:
    """TRUNCATE fact_match and reload from CSV. Returns row count."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Transformed CSV not found: {CSV_PATH}. "
            "Run `python -m etl.transform.run_transform` first."
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    # Ensure bool column is Python bool (not numpy bool / string)
    if "is_home" in df.columns:
        df["is_home"] = df["is_home"].map(
            lambda v: True if str(v).strip().lower() in ("true", "1") else
                      (False if str(v).strip().lower() in ("false", "0") else None)
        )

    # Ensure date is a string in ISO format (PostgreSQL DATE accepts 'YYYY-MM-DD')
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} CASCADE"))
        logger.info("TRUNCATED %s", TABLE_NAME)

    df.to_sql(
        TABLE_NAME,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )

    logger.info("Loaded %d rows into %s", len(df), TABLE_NAME)
    return len(df)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    load()


if __name__ == "__main__":
    main()
