"""
etl/transform/transform_statsbomb_matches.py
----------------------------------------------
Reads data/raw/statsbomb/argentina_statsbomb_matches.csv and appends
those matches to data/transformed/fact_match.csv (which already has
WCQ rows from transform_wcq_matches).

match_id uses the same ARG_YYYYMMDD_Opponent format as match_fbref_id
in the events CSV, so event_statsbomb FK resolution works.

Copa América and World Cup matches are neutral-venue → is_neutral=True.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

RAW_DIR         = PROJECT_ROOT / "data" / "raw" / "statsbomb"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"
INPUT_PATH      = RAW_DIR         / "argentina_statsbomb_matches.csv"
DIM_COMP_PATH   = TRANSFORMED_DIR / "dim_competition.csv"
FACT_MATCH_PATH = TRANSFORMED_DIR / "fact_match.csv"

# Map StatsBomb competition names + year to our dim_competition IDs
# (verified against dim_competition in DB)
_COMP_MAP = {
    ("copa america",  "2024"): 2,
    ("copa américa",  "2024"): 2,
    ("fifa world cup","2022"): 3,
}


def _result(gf: int, ga: int) -> str:
    if gf > ga: return "W"
    if gf == ga: return "D"
    return "L"


def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        logger.error("Missing %s — run extract_statsbomb_events first", INPUT_PATH)
        return pd.DataFrame()

    sb = pd.read_csv(INPUT_PATH, encoding="utf-8")

    rows = []
    for _, r in sb.iterrows():
        home  = str(r.get("home_team", "")).strip()
        away  = str(r.get("away_team", "")).strip()
        comp  = str(r.get("competition", "")).strip().lower()
        season = str(r.get("season", "")).strip()
        date  = str(r.get("date", ""))[:10]

        is_home   = "Argentina" in home
        opponent  = away if is_home else home

        home_sc = int(r.get("home_score", 0) or 0)
        away_sc = int(r.get("away_score", 0) or 0)
        goals_for     = home_sc if is_home else away_sc
        goals_against = away_sc if is_home else home_sc

        comp_id = _COMP_MAP.get((comp, season))
        if comp_id is None:
            logger.warning("No competition_id for '%s' '%s' — skipping", comp, season)
            continue

        # match_id must match match_fbref_id in events CSV
        match_id = str(r.get("match_fbref_id", "")).strip()
        if not match_id:
            logger.warning("Empty match_fbref_id for %s vs %s — skipping", home, away)
            continue

        rows.append({
            "match_id":       match_id,
            "date":           date,
            "competition_id": comp_id,
            "stage":          None,
            "is_home":        is_home,
            "is_neutral":     True,   # Copa/WC are neutral-venue tournaments
            "opponent":       opponent,
            "goals_for":      goals_for,
            "goals_against":  goals_against,
            "result":         _result(goals_for, goals_against),
            "xg_for":         None,
            "xg_against":     None,
            "possession_pct": None,
            "shots":          None,
            "shots_on_target": None,
            "venue":          None,
        })

    if not rows:
        logger.warning("No StatsBomb matches produced — check competition name mapping")
        return pd.DataFrame()

    df_new = pd.DataFrame(rows)
    logger.info("StatsBomb matches parsed: %d rows", len(df_new))

    # Load existing fact_match.csv and append (avoiding duplicates by match_id)
    if FACT_MATCH_PATH.exists():
        df_existing = pd.read_csv(FACT_MATCH_PATH, encoding="utf-8")
        existing_ids = set(df_existing["match_id"])
        df_new = df_new[~df_new["match_id"].isin(existing_ids)]
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(FACT_MATCH_PATH, index=False, encoding="utf-8")
    logger.info(
        "fact_match: %d total rows (%d new) -> %s",
        len(df_combined), len(df_new), FACT_MATCH_PATH,
    )
    return df_combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    transform()
