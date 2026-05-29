"""
etl/load/load_fact_player_match.py
------------------------------------
Loads fact_player_match from data/transformed/fact_player_match.csv
into PostgreSQL.

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
CSV_PATH = TRANSFORMED_DIR / "fact_player_match.csv"
TABLE_NAME = "fact_player_match"

# Integer columns that must not arrive as float (NaN would break INT cast)
_INT_COLS = [
    "player_id", "minutes_played",
    "goals", "assists", "shots", "shots_on_target",
    "passes_completed", "passes_attempted",
    "progressive_passes", "key_passes", "progressive_carries",
    "tackles", "interceptions", "blocks",
    "yellow_cards", "red_cards",
    "saves",
]

# Float/nullable columns
_FLOAT_COLS = ["xg", "xag", "pass_pct", "save_pct", "psxg"]


def load() -> int:
    """TRUNCATE fact_player_match and reload from CSV. Returns row count."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Transformed CSV not found: {CSV_PATH}. "
            "Run `python -m etl.transform.run_transform` first."
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    # Coerce integer counting columns — fill NaN with 0 before casting
    for col in _INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Coerce float columns — leave NaN as None (becomes SQL NULL)
    for col in _FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # boolean columns
    for bool_col in ("started", "clean_sheet"):
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].map(
                lambda v: True if str(v).strip().lower() in ("true", "1") else
                          (False if str(v).strip().lower() in ("false", "0") else None)
            )

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
