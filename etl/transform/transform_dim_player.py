"""
etl/transform/transform_dim_player.py
---------------------------------------
Reads the SQUAD registry from config/players.py and produces
data/transformed/dim_player.csv with one row per player.

Output columns:
    player_id, player_name, short_name, position,
    current_club, current_league, fbref_name, statsbomb_name
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Path setup — allow running as script or as module
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.players import SQUAD
from etl.extract.utils import normalize_name
from etl.transform.player_name_map import FBREF_TO_CANONICAL, STATSBOMB_TO_CANONICAL

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"
OUTPUT_PATH = TRANSFORMED_DIR / "dim_player.csv"


# ---------------------------------------------------------------------------
# Reverse maps: canonical → fbref/statsbomb source key (best guess)
# These let us pre-populate fbref_name / statsbomb_name from the maps.
# ---------------------------------------------------------------------------

def _build_reverse_map(fwd: dict[str, str]) -> dict[str, str]:
    """
    Build canonical → raw name mapping.
    Prefer the longest raw key (most specific) per canonical target.
    """
    rev: dict[str, str] = {}
    for raw, canonical in fwd.items():
        existing = rev.get(canonical, "")
        if len(raw) > len(existing):
            rev[canonical] = raw
    return rev


def transform() -> pd.DataFrame:
    """Build dim_player DataFrame from SQUAD and name maps."""

    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    rev_fbref = _build_reverse_map(FBREF_TO_CANONICAL)
    rev_statsbomb = _build_reverse_map(STATSBOMB_TO_CANONICAL)

    rows = []
    for idx, player in enumerate(SQUAD, start=1):
        canonical = player["player_name"]

        # FBRef name: use the canonical itself by default; override if a
        # specific longer raw key exists in the forward map.
        fbref_name = rev_fbref.get(canonical, canonical)

        # StatsBomb name: prefer explicit statsbomb_name from config, then map lookup.
        statsbomb_name = player.get("statsbomb_name") or rev_statsbomb.get(canonical, canonical)

        short_name = player.get("short_name") or canonical

        rows.append(
            {
                "player_id": idx,
                "player_name": canonical,
                "short_name": short_name,
                "position": player["position"],
                "current_club": player["club"],
                "current_league": player["league"],
                "fbref_name": fbref_name,
                "statsbomb_name": statsbomb_name,
            }
        )

    df = pd.DataFrame(rows)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("dim_player: %d rows → %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
