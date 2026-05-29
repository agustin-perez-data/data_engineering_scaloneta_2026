"""
etl/transform/transform_wcq_player_matches.py
-----------------------------------------------
Reads data/raw/wcq_player_matches.csv (from extract_espn_wcq_matches)
+ data/transformed/dim_player.csv (for player_id FK)
and writes data/transformed/fact_player_match.csv.

ESPN provides: started, minutes_played (derived), goals, yellow_cards, red_cards.
All other stats default to NULL/0 (not available from ESPN WCQ).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import normalize_name

logger = logging.getLogger(__name__)

RAW_DIR         = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"
INPUT_PATH      = RAW_DIR         / "wcq_player_matches.csv"
DIM_PLAYER_PATH = TRANSFORMED_DIR / "dim_player.csv"
OUTPUT_PATH     = TRANSFORMED_DIR / "fact_player_match.csv"

# All columns expected in the DB table
_OUT_COLS = [
    "match_id", "player_id", "started", "minutes_played",
    "goals", "assists", "shots", "shots_on_target",
    "xg", "xag",
    "passes_completed", "passes_attempted", "pass_pct",
    "progressive_passes", "key_passes", "progressive_carries",
    "tackles", "interceptions", "blocks",
    "yellow_cards", "red_cards",
    "saves", "save_pct", "clean_sheet", "psxg",
]


def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        logger.error("Missing %s — run extract_espn_wcq_matches first", INPUT_PATH)
        return pd.DataFrame()

    raw = pd.read_csv(INPUT_PATH, encoding="utf-8")

    # Build player_name → player_id lookup (normalized)
    dim = pd.read_csv(DIM_PLAYER_PATH, encoding="utf-8")
    name_to_id = dict(zip(dim["player_name"], dim["player_id"]))
    norm_to_id = {normalize_name(n): pid for n, pid in name_to_id.items()}

    rows = []
    unresolved = set()

    for _, r in raw.iterrows():
        pname = str(r.get("player_name", "")).strip()
        pid = name_to_id.get(pname) or norm_to_id.get(normalize_name(pname))
        if pid is None:
            unresolved.add(pname)
            continue

        mins = r.get("minutes_played")
        mins = int(mins) if pd.notna(mins) else None

        rows.append({
            "match_id":      r["match_id"],
            "player_id":     pid,
            "started":       bool(r.get("started", False)),
            "minutes_played": mins,
            # ESPN provides these directly
            "goals":         int(r.get("goals", 0) or 0),
            "yellow_cards":  int(r.get("yellow_cards", 0) or 0),
            "red_cards":     int(r.get("red_cards", 0) or 0),
            # Not available from ESPN WCQ
            "assists":       None,
            "shots":         None,
            "shots_on_target": None,
            "xg":            None,
            "xag":           None,
            "passes_completed":  None,
            "passes_attempted":  None,
            "pass_pct":      None,
            "progressive_passes":  None,
            "key_passes":    None,
            "progressive_carries": None,
            "tackles":       None,
            "interceptions": None,
            "blocks":        None,
            "saves":         None,
            "save_pct":      None,
            "clean_sheet":   None,
            "psxg":          None,
        })

    if unresolved:
        logger.info("Skipped %d names not in squad: %s", len(unresolved), sorted(unresolved))

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=_OUT_COLS)

    for col in _OUT_COLS:
        if col not in df.columns:
            df[col] = None
    df = df[_OUT_COLS]

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("fact_player_match: %d rows -> %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    transform()
