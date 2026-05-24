"""
etl/load/load_dimensions.py
-----------------------------
Loads dim_player and dim_competition from transformed CSVs
into the PostgreSQL database.

Strategy: TRUNCATE … CASCADE then INSERT via pandas to_sql(if_exists='append').
This preserves FK constraints defined in the schema.
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


def _load_table(
    csv_path: Path,
    table_name: str,
    dtype_overrides: dict | None = None,
) -> int:
    """
    TRUNCATE the target table then INSERT all rows from csv_path.

    Returns the number of rows inserted.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Transformed CSV not found: {csv_path}. "
            "Run `python -m etl.transform.run_transform` first."
        )

    df = pd.read_csv(csv_path, encoding="utf-8")
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        logger.info("TRUNCATED %s", table_name)

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        dtype=dtype_overrides,
        method="multi",
        chunksize=500,
    )

    logger.info("Loaded %d rows into %s", len(df), table_name)
    return len(df)


def load_dim_player() -> int:
    return _load_table(TRANSFORMED_DIR / "dim_player.csv", "dim_player")


def load_dim_competition() -> int:
    return _load_table(TRANSFORMED_DIR / "dim_competition.csv", "dim_competition")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    total = 0
    total += load_dim_player()
    total += load_dim_competition()
    logger.info("Dimensions loaded — %d total rows", total)


if __name__ == "__main__":
    main()
