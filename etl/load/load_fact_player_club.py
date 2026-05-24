"""
etl/load/load_fact_player_club.py
-----------------------------------
Loads fact_player_club_season from data/transformed/fact_player_club_season.csv
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
CSV_PATH = TRANSFORMED_DIR / "fact_player_club_season.csv"
TABLE_NAME = "fact_player_club_season"

# Columns that exist in the DB schema (matches schema.sql)
_DB_COLS = [
    "player_id", "season", "club", "league",
    "matches_played", "starts", "minutes",
    "goals", "assists", "xg", "xag",
    "shots", "shots_on_target", "pass_pct",
    "progressive_passes", "progressive_carries",
    "tackles", "interceptions",
    "yellow_cards", "red_cards",
    "saves", "save_pct", "clean_sheets", "goals_against_gk",
]

_INT_COLS = [
    "player_id", "matches_played", "starts", "minutes",
    "goals", "assists", "shots", "shots_on_target",
    "progressive_passes", "progressive_carries",
    "tackles", "interceptions",
    "yellow_cards", "red_cards",
    "saves", "clean_sheets", "goals_against_gk",
]

_FLOAT_COLS = ["xg", "xag", "pass_pct", "save_pct"]


def load() -> int:
    """TRUNCATE fact_player_club_season and reload from CSV. Returns row count."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Transformed CSV not found: {CSV_PATH}. "
            "Run `python -m etl.transform.run_transform` first."
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    # Rename minutes_played → minutes to match schema
    if "minutes_played" in df.columns and "minutes" not in df.columns:
        df = df.rename(columns={"minutes_played": "minutes"})

    # Only keep columns present in the DB schema
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
