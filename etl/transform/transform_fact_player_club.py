"""
etl/transform/transform_fact_player_club.py
---------------------------------------------
Reads data/raw/club_stats_all_leagues.csv + data/transformed/dim_player.csv
and writes data/transformed/fact_player_club_season.csv.

For each squad player we keep the row matching their current club/league
(from config/players.py).  Falls back to normalize_name matching if the
club field is absent or mismatched.

Output columns match the fact_player_club_season DB table:
    player_id, season, club, league,
    matches_played, starts, minutes_played,
    goals, assists, shots, shots_on_target, xg, xag,
    passes_completed, passes_attempted, pass_pct,
    progressive_passes, key_passes, progressive_carries,
    tackles, interceptions, blocks,
    yellow_cards, red_cards,
    saves, save_pct, clean_sheets, psxg
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.players import SQUAD, CURRENT_SEASON
from etl.extract.utils import normalize_name
from etl.transform.player_name_map import FBREF_TO_CANONICAL, resolve_player_name

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"

CLUB_STATS_CSV = RAW_DIR / "club_stats_all_leagues.csv"
DIM_PLAYER_CSV = TRANSFORMED_DIR / "dim_player.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "fact_player_club_season.csv"

# Counting stats → fill NaN with 0
_COUNT_COLS = [
    "matches_played", "starts", "minutes_played",
    "goals", "assists", "shots", "shots_on_target",
    "passes_completed", "passes_attempted",
    "progressive_passes", "key_passes", "progressive_carries",
    "tackles", "interceptions", "blocks",
    "yellow_cards", "red_cards",
    "saves", "clean_sheets", "goals_against_gk",
]

# Float stats → leave NaN as None
_FLOAT_COLS = ["xg", "xag", "pass_pct", "save_pct", "psxg"]


def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_").replace("%", "_pct") for c in df.columns]
    return df


def _find_col(candidates: list[str], df: pd.DataFrame) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not CLUB_STATS_CSV.exists():
        logger.error("Missing %s — run extract step first", CLUB_STATS_CSV)
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Load raw club stats
    # ------------------------------------------------------------------
    raw = pd.read_csv(CLUB_STATS_CSV, encoding="utf-8")
    raw = _normalise_cols(raw)

    player_col = _find_col(["player", "player_name", "name"], raw)
    club_col = _find_col(["squad", "club", "team"], raw)
    league_col = _find_col(["comp", "league", "competition"], raw)

    if player_col is None:
        raise ValueError(
            f"Cannot find player column in {CLUB_STATS_CSV}. "
            f"Available: {list(raw.columns)}"
        )

    # Build normalize_name → row-index list (a player may have multiple rows
    # in the CSV if they played for more than one club this season)
    raw["_norm_name"] = raw[player_col].apply(
        lambda n: normalize_name(str(n)) if pd.notna(n) else ""
    )
    if club_col:
        raw["_norm_club"] = raw[club_col].apply(
            lambda c: normalize_name(str(c)) if pd.notna(c) else ""
        )
    if league_col:
        raw["_norm_league"] = raw[league_col].apply(
            lambda l: normalize_name(str(l)) if pd.notna(l) else ""
        )

    # ------------------------------------------------------------------
    # Load dim_player for player_id lookup
    # ------------------------------------------------------------------
    dim_player = pd.read_csv(DIM_PLAYER_CSV, encoding="utf-8")
    name_to_id: dict[str, int] = dict(
        zip(dim_player["player_name"], dim_player["player_id"])
    )
    norm_to_id: dict[str, int] = {
        normalize_name(n): pid for n, pid in name_to_id.items()
    }

    # Column alias map
    col_map: dict[str, list[str]] = {
        "matches_played": ["mp", "matches", "matches_played", "g"],
        "starts": ["starts", "gs"],
        "minutes_played": ["min", "minutes", "minutes_played"],
        "goals": ["gls", "goals", "g"],
        "assists": ["ast", "assists"],
        "shots": ["sh", "shots"],
        "shots_on_target": ["sot", "shots_on_target"],
        "xg": ["xg", "expected_xg"],
        "xag": ["xag", "expected_xag"],
        "passes_completed": ["cmp", "passes_cmp", "passes_completed"],
        "passes_attempted": ["att", "passes_att", "passes_attempted"],
        "pass_pct": ["cmp_pct", "passes_cmp_pct", "pass_pct"],
        "progressive_passes": ["prg", "prgp", "progressive_passes"],
        "key_passes": ["kp", "key_passes"],
        "progressive_carries": ["prgc", "progressive_carries"],
        "tackles": ["tkl", "tackles"],
        "interceptions": ["int", "interceptions"],
        "blocks": ["blocks", "blk"],
        "yellow_cards": ["crdy", "yellow_cards"],
        "red_cards": ["crdr", "red_cards"],
        "saves": ["saves", "sav"],
        "save_pct": ["save_pct", "save_pct_pct"],
        "clean_sheets": ["cs", "clean_sheets", "clean_sheet"],
        "psxg": ["psxg", "post_shot_xg"],
    }

    def _get_col(stat: str) -> str | None:
        return _find_col(col_map.get(stat, [stat]), raw)

    def _read_stat(row: pd.Series, stat: str, is_float: bool = False):
        src_col = _get_col(stat)
        if src_col is None:
            return None if is_float else 0
        val = pd.to_numeric(row.get(src_col), errors="coerce")
        if pd.isna(val):
            return None if is_float else 0
        return float(val) if is_float else int(val)

    # ------------------------------------------------------------------
    # Build one output row per squad player
    # ------------------------------------------------------------------
    rows = []
    season_label = CURRENT_SEASON  # e.g. "2024-25"

    for player in SQUAD:
        canonical = player["player_name"]
        expected_club = player["club"]
        expected_league = player["league"]

        norm_canonical = normalize_name(canonical)
        norm_club = normalize_name(expected_club)

        # Find candidate rows in raw CSV
        candidates = raw[raw["_norm_name"] == norm_canonical].copy()

        if candidates.empty:
            # Try via FBREF_TO_CANONICAL reverse lookup
            for raw_name, c_name in FBREF_TO_CANONICAL.items():
                if c_name == canonical:
                    norm_raw = normalize_name(raw_name)
                    candidates = raw[raw["_norm_name"] == norm_raw].copy()
                    if not candidates.empty:
                        break

        if candidates.empty:
            logger.warning("No club stats found for %s", canonical)
            continue

        # Prefer the row for the player's current club
        if club_col and len(candidates) > 1:
            club_match = candidates[candidates["_norm_club"] == norm_club]
            selected = club_match.iloc[0] if not club_match.empty else candidates.iloc[0]
        else:
            selected = candidates.iloc[0]

        # Resolve player_id
        player_id = (
            name_to_id.get(canonical)
            or norm_to_id.get(norm_canonical)
        )
        if player_id is None:
            logger.warning("player_id not found for %s", canonical)
            continue

        out_row: dict = {
            "player_id": player_id,
            "season": season_label,
            "club": expected_club,
            "league": expected_league,
        }

        for stat in _COUNT_COLS:
            out_row[stat] = _read_stat(selected, stat, is_float=False)

        for stat in _FLOAT_COLS:
            out_row[stat] = _read_stat(selected, stat, is_float=True)

        rows.append(out_row)

    df = pd.DataFrame(rows)

    # Ensure all output columns exist
    all_cols = (
        ["player_id", "season", "club", "league"]
        + _COUNT_COLS
        + _FLOAT_COLS
    )
    for col in all_cols:
        if col not in df.columns:
            df[col] = None

    df = df[all_cols]

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("fact_player_club_season: %d rows → %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
