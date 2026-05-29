"""
etl/extract/sofascore_stats.py
--------------------------------
Season-specific club stats for non-Big5 players via Sofascore unofficial API.

Replaces the ESPN career-totals approach with per-season data, including
xG and xAG which ESPN could not provide.

Hardcoded player IDs and tournament/season IDs to avoid fragile search
lookups.  Update when players transfer leagues or a new season begins.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd
import requests

from config.players import SQUAD, LEAGUE_SEASON  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sofascore tournament + season IDs per league
# Multiple season_ids → stats are summed (e.g. ARG Clausura + Apertura)
# ---------------------------------------------------------------------------
SOFASCORE_LEAGUE_CONFIG: dict[str, dict] = {
    "ARG-Liga Profesional": {
        "tournament_id": 155,
        # Clausura 2025 (Jan-Jun) + Apertura 2025 (Jul-Dec)
        "season_ids": [77826, 70268],
    },
    "USA-Major League Soccer": {
        "tournament_id": 242,
        "season_ids": [70158],   # MLS 2025
    },
    "POR-Primeira Liga": {
        "tournament_id": 238,
        "season_ids": [63670],   # Liga Portugal 24/25
    },
    "BRA-Série A": {
        "tournament_id": 325,
        "season_ids": [72034],   # Brasileirão Serie A 2025
    },
}

# Canonical name → Sofascore player ID
# Verified manually; update if player changes clubs across a season boundary.
SOFASCORE_PLAYER_IDS: dict[str, int] = {
    "Gonzalo Montiel":    822933,
    "Leandro Paredes":    255389,
    "José Manuel López":  1094179,   # "José López" at Palmeiras in Sofascore
    "Lionel Messi":        12994,
    "Rodrigo De Paul":    249399,
    "Nicolás Otamendi":    74915,
}

# Sofascore stat key → our schema column
SOFASCORE_STAT_MAP: dict[str, str] = {
    "appearances":              "matches_played",
    "matchesStarted":           "starts",
    "minutesPlayed":            "minutes",
    "goals":                    "goals",
    "assists":                  "assists",
    "expectedGoals":            "xg",
    "expectedAssists":          "xag",
    "totalShots":               "shots",
    "shotsOnTarget":            "shots_on_target",
    "accuratePassesPercentage": "pass_pct",
    "keyPasses":                "key_passes",
    "tackles":                  "tackles",
    "interceptions":            "interceptions",
    "yellowCards":              "yellow_cards",
    "directRedCards":           "red_cards",
    "outfielderBlocks":         "blocks",
    # GK
    "saves":                    "saves",
    "cleanSheet":               "clean_sheets",
    "goalsConceded":            "goals_against_gk",
}

# Rate stats: weighted-average across multiple seasons instead of summing
_RATE_STATS = {"pass_pct", "save_pct"}

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


def _get(url: str, pause: float = 1.5) -> Optional[dict]:
    time.sleep(pause)
    try:
        resp = _session().get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("Sofascore GET failed %s — %s", url, exc)
        return None


def _player_stats_for_season(
    player_id: int,
    tournament_id: int,
    season_id: int,
) -> dict[str, float]:
    """Fetch flat stats dict for one player/tournament/season combination."""
    data = _get(
        f"https://api.sofascore.com/api/v1/player/{player_id}"
        f"/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
    )
    if not data:
        return {}
    raw = data.get("statistics", {})
    result: dict[str, float] = {}
    for ss_key, schema_col in SOFASCORE_STAT_MAP.items():
        val = raw.get(ss_key)
        if val is not None:
            try:
                result[schema_col] = float(val)
            except (TypeError, ValueError):
                pass
    return result


def _aggregate_seasons(season_stats: list[dict[str, float]]) -> dict[str, float]:
    """Combine stats across multiple seasons (e.g. Clausura + Apertura).

    Count and accumulated stats (goals, xG, minutes, …) are summed.
    Rate stats (pass_pct) are weighted by minutes_played.
    """
    if not season_stats:
        return {}
    if len(season_stats) == 1:
        return season_stats[0]

    result: dict[str, float] = {}
    all_keys = {k for d in season_stats for k in d}

    for key in all_keys:
        if key in _RATE_STATS:
            continue
        values = [d[key] for d in season_stats if key in d]
        result[key] = sum(values)

    # Weighted pass_pct by minutes (if available)
    if "pass_pct" in all_keys:
        weighted_sum = total_minutes = 0.0
        for d in season_stats:
            pct = d.get("pass_pct")
            mins = d.get("minutes", 0.0)
            if pct is not None and mins:
                weighted_sum += pct * mins
                total_minutes += mins
        if total_minutes > 0:
            result["pass_pct"] = weighted_sum / total_minutes
        else:
            # Fallback: simple average
            pcts = [d["pass_pct"] for d in season_stats if "pass_pct" in d]
            if pcts:
                result["pass_pct"] = sum(pcts) / len(pcts)

    return result


def scrape_sofascore(league: str, season: str) -> Optional[pd.DataFrame]:
    """Return season-specific stats for squad players in the given league.

    Args:
        league:  Our canonical league code (e.g. "ARG-Liga Profesional").
        season:  Our season string (e.g. "2025") — used only for logging.

    Returns:
        DataFrame with schema columns, or None if nothing collected.
    """
    config = SOFASCORE_LEAGUE_CONFIG.get(league)
    if config is None:
        logger.warning("Sofascore: no config for league %s", league)
        return None

    tournament_id = config["tournament_id"]
    season_ids = config["season_ids"]

    squad_in_league = [p for p in SQUAD if p["league"] == league]
    logger.info(
        "Sofascore: %s (%s) — %d squad players, seasons %s",
        league, season, len(squad_in_league), season_ids,
    )

    rows: list[dict] = []
    for player in squad_in_league:
        name = player["player_name"]
        player_id = SOFASCORE_PLAYER_IDS.get(name)
        if player_id is None:
            logger.warning("Sofascore: no player_id configured for %s", name)
            continue

        # Collect stats from each season_id
        season_stats: list[dict[str, float]] = []
        for sid in season_ids:
            stats = _player_stats_for_season(player_id, tournament_id, sid)
            if stats:
                season_stats.append(stats)
            else:
                logger.debug("Sofascore: no stats for %s in season %d", name, sid)

        if not season_stats:
            logger.warning("Sofascore: no stats found for %s", name)
            continue

        agg = _aggregate_seasons(season_stats)

        row: dict = {
            "player_name": name,
            "team":        player["club"],
            "league":      league,
            "season":      season,
        }
        row.update(agg)
        rows.append(row)

        logger.info(
            "  Sofascore %-25s  apps=%s  goals=%s  assists=%s  xG=%.2f",
            name,
            int(agg.get("matches_played", 0)),
            int(agg.get("goals", 0)),
            int(agg.get("assists", 0) if agg.get("assists") else 0),
            agg.get("xg", 0.0),
        )

    if not rows:
        return None

    return pd.DataFrame(rows)
