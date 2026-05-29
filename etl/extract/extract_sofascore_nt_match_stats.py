"""
etl/extract/extract_sofascore_nt_match_stats.py
-------------------------------------------------
Per-match Argentina NT player stats via Sofascore lineups API.

Covers competitions NOT available in StatsBomb open data:
  - Copa América 2021  (4 matches)
  - WCQ CONMEBOL 2022  (18 matches)
  - WCQ CONMEBOL 2026  (18 matches)

Output: data/raw/sofascore_nt_match_stats.csv
Schema: same as argentina_player_match_stats.csv
  match_id, player_name, date, competition, opponent,
  started, position, minutes_played,
  goals, assists, shots, shots_on_target,
  passes_completed, passes_attempted, key_passes,
  tackles, interceptions, blocks,
  yellow_cards, red_cards,
  saves, goals_against_gk, clean_sheet

Note: xG and xAG are not available from Sofascore match lineups.
"""

from __future__ import annotations

import datetime
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.players import SQUAD  # noqa: E402
from etl.extract.utils import normalize_name  # noqa: E402

logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "sofascore_nt_match_stats.csv"

SQUAD_NORMS: set[str] = {normalize_name(p["player_name"]) for p in SQUAD}
GK_NORMS: set[str] = {normalize_name(p["player_name"]) for p in SQUAD if p["position"] == "GK"}
_NORM_TO_CANONICAL: dict[str, str] = {normalize_name(p["player_name"]): p["player_name"] for p in SQUAD}

ARGENTINA_TEAM_ID = 4819

# ---------------------------------------------------------------------------
# Hardcoded Sofascore event IDs for each Argentina match per competition
# format: (sofascore_event_id, date_str, opponent_name)
# ---------------------------------------------------------------------------

COPA_AMERICA_2021: list[tuple[int, str, str]] = [
    (8516467, "2021-06-14", "Chile"),
    (8516470, "2021-06-19", "Uruguay"),
    (8516473, "2021-06-22", "Paraguay"),
    (9554796, "2021-06-29", "Bolivia"),
]

WCQ_2022_EVENTS: list[tuple[int, str, str]] = [
    (8899381, "2020-10-09", "Ecuador"),
    (9015915, "2020-10-13", "Bolivia"),
    (8545976, "2020-11-13", "Paraguay"),
    (8545977, "2020-11-18", "Peru"),
    (9809983, "2021-10-10", "Uruguay"),
    (8545996, "2021-06-04", "Chile"),
    (8546001, "2021-06-08", "Colombia"),
    (8546002, "2021-09-03", "Venezuela"),
    (8546011, "2021-09-09", "Bolivia"),
    (8546012, "2021-10-07", "Paraguay"),
    (8546021, "2021-10-14", "Peru"),
    (8524233, "2021-11-12", "Uruguay"),
    (8524253, "2021-11-16", "Brazil"),
    (8524251, "2022-01-28", "Chile"),
    (8524242, "2022-02-01", "Colombia"),
    (8524236, "2022-03-25", "Venezuela"),
    (8524227, "2022-03-29", "Ecuador"),
]

WCQ_2026_EVENTS: list[tuple[int, str, str]] = [
    (11518404, "2023-09-08", "Ecuador"),
    (11518411, "2023-09-12", "Bolivia"),
    (11620301, "2023-10-12", "Paraguay"),
    (11620291, "2023-10-18", "Peru"),
    (11774450, "2023-11-17", "Uruguay"),
    (11774480, "2023-11-22", "Brazil"),
    (12716816, "2024-09-06", "Chile"),
    (12716821, "2024-09-10", "Colombia"),
    (12851464, "2024-10-10", "Venezuela"),
    (12851457, "2024-10-16", "Bolivia"),
    (12977649, "2024-11-14", "Paraguay"),
    (12995973, "2024-11-20", "Peru"),
    (13129487, "2025-03-21", "Uruguay"),
    (13129495, "2025-03-26", "Brazil"),
    (13856223, "2025-06-06", "Chile"),
    (13856224, "2025-06-11", "Colombia"),
    (14169215, "2025-09-04", "Venezuela"),
    (14169218, "2025-09-09", "Ecuador"),
]

TARGETS: list[tuple[str, list[tuple[int, str, str]]]] = [
    ("Copa América 2021",                    COPA_AMERICA_2021),
    ("World Cup Qualifying 2022 - CONMEBOL", WCQ_2022_EVENTS),
    ("World Cup Qualifying - CONMEBOL",      WCQ_2026_EVENTS),
]

# Sofascore stat → schema column
STAT_MAP: dict[str, str] = {
    "goals":                  "goals",
    "goalAssist":             "assists",
    "onTargetScoringAttempt": "shots_on_target",
    "totalShots":             "shots",
    "accuratePass":           "passes_completed",
    "totalPass":              "passes_attempted",
    "keyPass":                "key_passes",
    "totalTackle":            "tackles",
    "interceptionWon":        "interceptions",
    "outfielderBlock":        "blocks",
    "yellowCard":             "yellow_cards",
    "redCard":                "red_cards",
    # GK
    "saves":                  "saves",
}

_SESSION: Optional[requests.Session] = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })
    return _SESSION


def _get(url: str, pause: float = 1.2) -> Optional[dict]:
    time.sleep(pause)
    try:
        resp = _session().get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("GET failed %s — %s", url, exc)
        return None


def _build_match_id(date_str: str, opponent: str) -> str:
    date_part = date_str.replace("-", "")
    opp_part = re.sub(r"\s+", "_", opponent.strip())[:10]
    return f"ARG_{date_part}_{opp_part}"


def _resolve_name(raw_name: str) -> str | None:
    norm = normalize_name(raw_name)
    if norm in SQUAD_NORMS:
        return _NORM_TO_CANONICAL.get(norm)
    # word-subset fallback (handles full names like 'Lionel Andrés Messi Cuccittini')
    raw_words = set(norm.split())
    for sq_norm in SQUAD_NORMS:
        if set(sq_norm.split()).issubset(raw_words):
            return _NORM_TO_CANONICAL.get(sq_norm)
    return None


def _process_event(
    event_id: int,
    date_str: str,
    opponent: str,
    competition: str,
) -> list[dict]:
    """Fetch lineups for one match and return per-player stat rows."""
    data = _get(f"https://api.sofascore.com/api/v1/event/{event_id}/lineups")
    if not data:
        logger.warning("No lineups for event %d (%s vs %s)", event_id, date_str, opponent)
        return []

    match_id = _build_match_id(date_str, opponent)
    rows: list[dict] = []

    # Determine which side is Argentina
    home_side = data.get("home", {})
    away_side = data.get("away", {})

    # Count squad players in each side to identify Argentina
    def _arg_count(side: dict) -> int:
        return sum(
            1 for p in side.get("players", [])
            if _resolve_name(p.get("player", {}).get("name", ""))
        )

    arg_side = home_side if _arg_count(home_side) >= _arg_count(away_side) else away_side
    opp_side = away_side if arg_side is home_side else home_side

    # Goals conceded = goals scored by opponent
    opp_goals = sum(
        p.get("statistics", {}).get("goals", 0)
        for p in opp_side.get("players", [])
    )

    for player_entry in arg_side.get("players", []):
        raw_name = player_entry.get("player", {}).get("name", "")
        canonical = _resolve_name(raw_name)
        if canonical is None:
            continue

        stats = player_entry.get("statistics", {})
        is_substitute = player_entry.get("substitute", False)
        position = player_entry.get("position", "")

        minutes = int(stats.get("minutesPlayed") or (45 if is_substitute else 90))
        is_gk = normalize_name(canonical) in GK_NORMS

        row: dict = {
            "match_id":         match_id,
            "player_name":      canonical,
            "date":             date_str,
            "competition":      competition,
            "opponent":         opponent,
            "started":          not is_substitute,
            "position":         position or None,
            "minutes_played":   minutes,
            "goals":            int(stats.get("goals", 0)),
            "assists":          int(stats.get("goalAssist", 0)),
            "shots":            int(stats.get("totalShots", 0)),
            "shots_on_target":  int(stats.get("onTargetScoringAttempt", 0)),
            "xg":               None,   # not available per-match in Sofascore
            "xag":              None,
            "passes_completed": int(stats.get("accuratePass", 0)),
            "passes_attempted": int(stats.get("totalPass", 0)),
            "key_passes":       int(stats.get("keyPass", 0)),
            "progressive_passes": 0,
            "tackles":          int(stats.get("totalTackle", 0)),
            "interceptions":    int(stats.get("interceptionWon", 0)),
            "blocks":           int(stats.get("outfielderBlock", 0)),
            "yellow_cards":     int(stats.get("yellowCard", 0)),
            "red_cards":        int(stats.get("redCard", 0)),
            # GK only
            "saves":            int(stats.get("saves", 0)) if is_gk else None,
            "goals_against_gk": opp_goals if is_gk else None,
            "clean_sheet":      (opp_goals == 0) if is_gk else None,
        }
        rows.append(row)

    logger.info(
        "  %s %s vs %s → %d Argentina players",
        date_str, "Argentina", opponent, len(rows),
    )
    return rows


def extract_sofascore_nt_stats() -> pd.DataFrame:
    all_rows: list[dict] = []

    for competition, events in TARGETS:
        logger.info("Processing %s (%d matches)", competition, len(events))
        for event_id, date_str, opponent in events:
            rows = _process_event(event_id, date_str, opponent, competition)
            all_rows.extend(rows)

    if not all_rows:
        logger.warning("No NT stats collected from Sofascore")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    logger.info("Sofascore NT stats: %d player-match rows across %d competitions", len(df), len(TARGETS))
    return df


def save(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved %d rows → %s", len(df), OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    df = extract_sofascore_nt_stats()
    save(df)
