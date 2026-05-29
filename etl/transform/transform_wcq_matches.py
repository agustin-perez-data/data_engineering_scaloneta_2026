"""
etl/transform/transform_wcq_matches.py
----------------------------------------
Reads data/raw/wcq_matches.csv (from extract_espn_wcq_matches)
and writes data/transformed/fact_match.csv.

Adds: is_home (bool), result (W/D/L), and NULL placeholders for
columns the ESPN source doesn't provide (xg, shots, stage).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

RAW_DIR         = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"
INPUT_PATH  = RAW_DIR         / "wcq_matches.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "fact_match.csv"


def _result(gf: int, ga: int) -> str:
    if gf > ga: return "W"
    if gf == ga: return "D"
    return "L"


def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        logger.error("Missing %s — run extract_espn_wcq_matches first", INPUT_PATH)
        return pd.DataFrame()

    df = pd.read_csv(INPUT_PATH, encoding="utf-8")

    df["is_home"]    = df["home_away"] == "home"
    df["is_neutral"] = False
    df["result"]     = df.apply(lambda r: _result(r["goals_for"], r["goals_against"]), axis=1)
    df["stage"]      = None
    df["xg_for"]     = None
    df["xg_against"] = None
    df["possession_pct"] = None
    df["shots"]          = None
    df["shots_on_target"] = None

    # Drop intermediate column
    df = df.drop(columns=["home_away"])

    out_cols = [
        "match_id", "date", "competition_id", "stage",
        "is_home", "is_neutral", "opponent",
        "goals_for", "goals_against", "result",
        "xg_for", "xg_against", "possession_pct",
        "shots", "shots_on_target", "venue",
    ]
    for col in out_cols:
        if col not in df.columns:
            df[col] = None
    df = df[out_cols]

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("fact_match: %d rows -> %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    transform()
