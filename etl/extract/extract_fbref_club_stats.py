"""
etl/extract/extract_fbref_club_stats.py
-----------------------------------------
Latest-season club stats for all squad players using Understat (Big 5) plus
stub rows for non-Big5 players so every player has a record in the DB.

Output: data/raw/club_stats_all_leagues.csv
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import flatten_soccerdata, normalize_name  # noqa: E402
from config.players import SQUAD, LEAGUE_SEASON, BIG5_LEAGUES  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "club_stats_all_leagues.csv"

SQUAD_NAMES_NORM: set[str] = {normalize_name(p["player_name"]) for p in SQUAD}

# Understat league code → soccerdata league code
UNDERSTAT_LEAGUES = {
    "ENG-Premier League": "ENG-Premier League",
    "ESP-La Liga":        "ESP-La Liga",
    "ITA-Serie A":        "ITA-Serie A",
    "FRA-Ligue 1":        "FRA-Ligue 1",
    "GER-Bundesliga":     "GER-Bundesliga",
}

FINAL_COLS = [
    "player_name", "team", "league", "season",
    "matches_played", "starts", "minutes",
    "goals", "assists", "xg", "xag",
    "shots", "shots_on_target",
    "pass_pct", "progressive_passes", "progressive_carries",
    "tackles", "interceptions",
    "yellow_cards", "red_cards",
    "saves", "save_pct", "clean_sheets", "goals_against_gk",
]


def _safe_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _scrape_understat(league: str, season: str) -> Optional[pd.DataFrame]:
    """Fetch player season stats from Understat via soccerdata."""
    try:
        import soccerdata as sd
    except ImportError:
        logger.error("soccerdata not installed")
        return None

    logger.info("Understat: %s  %s", league, season)
    try:
        src = sd.Understat(leagues=league, seasons=season)
        df = src.read_player_season_stats()
    except Exception as exc:
        logger.warning("Understat %s/%s failed: %s", league, season, exc)
        return None

    df = flatten_soccerdata(df)
    logger.info("  raw shape: %s  columns: %s", df.shape, list(df.columns[:15]))

    # Locate player column
    player_col = _find_col(df, "player", "player_name", "players", "name")
    if player_col is None:
        logger.warning("  Cannot find player column in Understat data for %s", league)
        return None

    # Filter to squad players
    mask = df[player_col].apply(lambda n: normalize_name(str(n)) in SQUAD_NAMES_NORM)
    df = df[mask].copy()
    if df.empty:
        logger.info("  No squad players found in %s", league)
        return None

    # Rename to standard schema columns
    renames: dict[str, str] = {}

    def _try(*candidates: str, out: str) -> None:
        for c in candidates:
            if c in df.columns:
                renames[c] = out
                break

    _try("player", "player_name", "players", "name", out="player_name")
    _try("team", "squad", "club", out="team")
    _try("season", "year", out="season")
    _try("games", "matches", "mp", "games_played", out="matches_played")
    _try("time", "minutes", "min", out="minutes")
    _try("goals", "gls", out="goals")
    _try("xg", "expected_goals", "npxg", out="xg")
    _try("assists", "ast", out="assists")
    _try("xa", "xag", "expected_assists", out="xag")
    _try("shots", "sh", out="shots")
    _try("key_passes", "kp", out="shots_on_target")  # Understat has key_passes not SOT
    _try("yellow", "crdy", "yel", out="yellow_cards")
    _try("red", "crdr", "red_cards_x", out="red_cards")

    df = df.rename(columns=renames)

    # Ensure player_name is set
    if "player_name" not in df.columns and player_col in df.columns:
        df = df.rename(columns={player_col: "player_name"})

    df["league"] = league
    if "season" not in df.columns:
        df["season"] = season

    logger.info("  Found %d squad players in %s", len(df), league)
    return df


def _make_stub_rows(non_big5_players: list[dict]) -> pd.DataFrame:
    """Create placeholder rows for players not covered by Understat."""
    rows = []
    for p in non_big5_players:
        rows.append({
            "player_name": p["player_name"],
            "team": p["club"],
            "league": p["league"],
            "season": LEAGUE_SEASON.get(p["league"], "2024-25"),
            "matches_played": None,
            "starts": None,
            "minutes": None,
            "goals": None,
            "assists": None,
            "xg": None,
            "xag": None,
            "shots": None,
            "shots_on_target": None,
            "pass_pct": None,
            "progressive_passes": None,
            "progressive_carries": None,
            "tackles": None,
            "interceptions": None,
            "yellow_cards": None,
            "red_cards": None,
            "saves": None,
            "save_pct": None,
            "clean_sheets": None,
            "goals_against_gk": None,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def extract_club_stats() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    covered_names: set[str] = set()

    # Understat for Big 5 leagues
    for league in BIG5_LEAGUES:
        season = LEAGUE_SEASON.get(league, "2024-25")
        df = _scrape_understat(league, season)
        if df is not None and not df.empty:
            frames.append(df)
            for name in df["player_name"].tolist():
                covered_names.add(normalize_name(str(name)))

    # Stub rows for players in non-Big5 leagues
    non_big5 = [p for p in SQUAD if p["league"] not in BIG5_LEAGUES]
    logger.info("Non-Big5 players (stub rows): %d", len(non_big5))
    stubs = _make_stub_rows(non_big5)
    if not stubs.empty:
        frames.append(stubs)

    if not frames:
        logger.error("No club stats collected")
        return pd.DataFrame(columns=FINAL_COLS)

    combined = pd.concat(frames, ignore_index=True)

    for col in FINAL_COLS:
        if col not in combined.columns:
            combined[col] = None

    num_cols = [c for c in FINAL_COLS if c not in ("player_name", "team", "league", "season")]
    for col in num_cols:
        combined[col] = _safe_float(combined[col])

    combined = combined[FINAL_COLS].reset_index(drop=True)
    logger.info("Club stats final shape: %s", combined.shape)
    return combined


def save(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved %d rows → %s", len(df), OUT_FILE)


if __name__ == "__main__":
    df = extract_club_stats()
    save(df)
