"""
etl/extract/extract_fbref_player_nt_stats.py
---------------------------------------------
Derives per-match player stats for Argentina national team from StatsBomb events.

Coverage:
  - FIFA World Cup 2022
  - Copa América 2024

Outputs:
  data/raw/argentina_player_match_stats.csv   — outfield + GK combined
  data/raw/argentina_gk_match_stats.csv       — GK-specific stats
"""

from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import normalize_name  # noqa: E402
from config.players import SQUAD  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE_OUTFIELD = OUT_DIR / "argentina_player_match_stats.csv"
OUT_FILE_GK = OUT_DIR / "argentina_gk_match_stats.csv"

SQUAD_NAMES_NORM: set[str] = {normalize_name(p["player_name"]) for p in SQUAD}
GK_NAMES_NORM: set[str] = {
    normalize_name(p["player_name"]) for p in SQUAD if p["position"] == "GK"
}

# StatsBomb targets: (competition_id, season_id, comp_label)
SB_TARGETS = [
    (43,  106, "FIFA World Cup"),
    (223, 282, "Copa América 2024"),
]

EVENT_PAUSE = 1.5  # seconds between match event requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_match_id(date_str: str, opponent: str) -> str:
    date_part = str(date_str).replace("-", "")
    opp_part = re.sub(r"\s+", "_", str(opponent).strip())[:10]
    return f"ARG_{date_part}_{opp_part}"


def _get_nested(obj: Any, *keys: str) -> Any:
    """Safely traverse nested dicts."""
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj


def _dict_name(obj: Any) -> str:
    if isinstance(obj, dict):
        return obj.get("name", "")
    return str(obj or "")


def _opponent_name(match_row: pd.Series) -> str:
    home = str(match_row.get("home_team", ""))
    away = str(match_row.get("away_team", ""))
    return away if "Argentina" in home else home


# ---------------------------------------------------------------------------
# Per-match aggregation
# ---------------------------------------------------------------------------

def _aggregate_match(sb, match_id: int, match_date: str, opponent: str, comp: str) -> list[dict]:
    """Return list of player-stat dicts for one Argentina match."""
    time.sleep(EVENT_PAUSE)

    try:
        events_df = sb.events(match_id=match_id)
        lineups = sb.lineups(match_id=match_id)
    except Exception as exc:
        logger.warning("Match %d events failed: %s", match_id, exc)
        return []

    if not isinstance(events_df, pd.DataFrame) or events_df.empty:
        return []

    arg_lineup: pd.DataFrame = lineups.get("Argentina", pd.DataFrame())
    if arg_lineup.empty:
        return []

    # Build player registry from lineup
    players: dict[int, dict] = {}
    for _, p in arg_lineup.iterrows():
        pid = p.get("player_id")
        if pid is None or (isinstance(pid, float) and pd.isna(pid)):
            continue
        positions = p.get("positions", []) or []
        pos = ""
        if positions:
            first = positions[0]
            if isinstance(first, dict):
                pos_obj = first.get("position", {})
                pos = pos_obj.get("name", "") if isinstance(pos_obj, dict) else str(pos_obj)
            else:
                pos = str(first)
        players[int(pid)] = {
            "player_name": p.get("player_name", ""),
            "position": pos,
            "started": False,
            "minutes_played": 0,
            "goals": 0, "assists": 0,
            "shots": 0, "shots_on_target": 0,
            "xg": 0.0, "xag": 0.0,
            "passes_completed": 0, "passes_attempted": 0,
            "key_passes": 0, "progressive_passes": 0,
            "tackles": 0, "interceptions": 0, "blocks": 0,
            "yellow_cards": 0, "red_cards": 0,
            # GK
            "saves": 0, "goals_against_gk": 0, "clean_sheet": False,
        }

    # Determine starting XI and minutes from Starting XI + Substitution events
    for _, ev in events_df.iterrows():
        etype = _dict_name(ev.get("type") if isinstance(ev.get("type"), dict) else {"name": ev.get("type_name", ev.get("type", ""))})
        team = _dict_name(ev.get("team") if isinstance(ev.get("team"), dict) else {"name": ev.get("team_name", ev.get("team", ""))})

        if team != "Argentina":
            continue

        player_raw = ev.get("player")
        pid = _get_nested(player_raw, "id") if isinstance(player_raw, dict) else ev.get("player_id")
        if pid is not None and not (isinstance(pid, float) and pd.isna(pid)):
            pid = int(pid)
        else:
            pid = None

        minute = int(ev.get("minute", 0) or 0)

        if etype == "Starting XI":
            tactics = ev.get("tactics")
            if isinstance(tactics, dict):
                for li in tactics.get("lineup", []):
                    lp = li.get("player", {})
                    lp_id = int(lp.get("id", -1))
                    if lp_id in players:
                        players[lp_id]["started"] = True
                        players[lp_id]["minutes_played"] = 90

        elif etype == "Substitution":
            # Player subbed off
            if pid and pid in players:
                players[pid]["minutes_played"] = minute
            # Player coming on
            sub_data = ev.get("substitution", {})
            if isinstance(sub_data, dict):
                replacement = sub_data.get("replacement", {})
                rep_id = _get_nested(replacement, "id") if isinstance(replacement, dict) else None
                if rep_id:
                    rep_id = int(rep_id)
                    if rep_id in players:
                        players[rep_id]["minutes_played"] = 90 - minute

    # Default minutes for starters not updated by Starting XI event
    for pid, info in players.items():
        if info["started"] and info["minutes_played"] == 0:
            info["minutes_played"] = 90
        elif not info["started"] and info["minutes_played"] == 0:
            info["minutes_played"] = 30  # conservative default for sub

    # Aggregate events
    argentina_events = events_df[
        events_df.apply(
            lambda r: _dict_name(r.get("team") if isinstance(r.get("team"), dict) else {"name": r.get("team_name", r.get("team", ""))}) == "Argentina",
            axis=1,
        )
    ]

    for _, ev in argentina_events.iterrows():
        player_raw = ev.get("player")
        pid = _get_nested(player_raw, "id") if isinstance(player_raw, dict) else ev.get("player_id")
        if pid is None or (isinstance(pid, float) and pd.isna(pid)):
            continue
        pid = int(pid)
        if pid not in players:
            continue

        etype = _dict_name(ev.get("type") if isinstance(ev.get("type"), dict) else {"name": ev.get("type_name", ev.get("type", ""))})

        if etype == "Shot":
            players[pid]["shots"] += 1
            shot = ev.get("shot", {})
            if isinstance(shot, dict):
                xg = float(shot.get("statsbomb_xg") or 0)
                players[pid]["xg"] += xg
                outcome_name = _dict_name(shot.get("outcome"))
                if outcome_name == "Goal":
                    players[pid]["goals"] += 1
                    players[pid]["shots_on_target"] += 1
                elif "Saved" in outcome_name:
                    players[pid]["shots_on_target"] += 1

        elif etype == "Pass":
            players[pid]["passes_attempted"] += 1
            pass_data = ev.get("pass", {})
            if isinstance(pass_data, dict):
                outcome_name = _dict_name(pass_data.get("outcome")) if pass_data.get("outcome") else ""
                if not outcome_name:
                    players[pid]["passes_completed"] += 1
                if pass_data.get("goal_assist"):
                    players[pid]["assists"] += 1
                    xa = float(pass_data.get("shot_assist_xg") or 0)
                    players[pid]["xag"] += xa
                if pass_data.get("key_pass"):
                    players[pid]["key_passes"] += 1
                if pass_data.get("through_ball") or (pass_data.get("length") or 0) > 20:
                    pass  # progressive pass approximation skipped

        elif etype == "Pressure":
            pass  # skip defensive events for now

        elif etype == "Ball Recovery":
            players[pid]["interceptions"] += 1

        elif etype == "Goal Keeper":
            gk_data = ev.get("goalkeeper", {})
            if isinstance(gk_data, dict):
                outcome_name = _dict_name(gk_data.get("outcome"))
                if "Saved" in outcome_name:
                    players[pid]["saves"] += 1

        elif etype == "Bad Behaviour":
            bad = ev.get("bad_behaviour", {})
            if isinstance(bad, dict):
                card_name = _dict_name(bad.get("card"))
                if "Yellow" in card_name:
                    players[pid]["yellow_cards"] += 1
                elif "Red" in card_name:
                    players[pid]["red_cards"] += 1

    # Determine clean sheet for GKs
    # Count goals conceded by Argentina (opponent's shots with Goal outcome)
    opp_shots = events_df[
        events_df.apply(
            lambda r: _dict_name(r.get("type") if isinstance(r.get("type"), dict) else {"name": r.get("type_name", r.get("type", ""))}) == "Shot"
            and _dict_name(r.get("team") if isinstance(r.get("team"), dict) else {"name": r.get("team_name", r.get("team", ""))}) != "Argentina",
            axis=1,
        )
    ]
    goals_conceded = sum(
        1 for _, r in opp_shots.iterrows()
        if _dict_name(r.get("shot", {}).get("outcome") if isinstance(r.get("shot"), dict) else {}) == "Goal"
    )

    fbref_mid = _build_match_id(match_date, opponent)

    rows = []
    for pid, info in players.items():
        norm = normalize_name(info["player_name"])
        if norm not in SQUAD_NAMES_NORM:
            continue

        is_gk = norm in GK_NAMES_NORM
        if is_gk:
            info["clean_sheet"] = goals_conceded == 0
            info["goals_against_gk"] = goals_conceded

        rows.append({
            "match_id": fbref_mid,
            "player_name": info["player_name"],
            "date": match_date,
            "competition": comp,
            "opponent": opponent,
            "started": info["started"],
            "position": info["position"],
            "minutes_played": info["minutes_played"],
            "goals": info["goals"],
            "assists": info["assists"],
            "shots": info["shots"],
            "shots_on_target": info["shots_on_target"],
            "xg": round(info["xg"], 3),
            "xag": round(info["xag"], 3),
            "passes_completed": info["passes_completed"],
            "passes_attempted": info["passes_attempted"],
            "key_passes": info["key_passes"],
            "progressive_passes": info["progressive_passes"],
            "tackles": info["tackles"],
            "interceptions": info["interceptions"],
            "blocks": info["blocks"],
            "yellow_cards": info["yellow_cards"],
            "red_cards": info["red_cards"],
            # GK only
            "saves": info["saves"] if is_gk else None,
            "goals_against_gk": info["goals_against_gk"] if is_gk else None,
            "clean_sheet": info["clean_sheet"] if is_gk else None,
        })

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_outfield_stats(session=None) -> pd.DataFrame:
    """Run extraction and return outfield stats DataFrame."""
    return _run_extraction()[0]


def extract_gk_stats(session=None) -> pd.DataFrame:
    """Run extraction and return GK stats DataFrame."""
    return _run_extraction()[1]


def _run_extraction() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        from statsbombpy import sb
    except ImportError:
        logger.error("statsbombpy not installed")
        return pd.DataFrame(), pd.DataFrame()

    all_rows: list[dict] = []

    for comp_id, season_id, comp_label in SB_TARGETS:
        logger.info("Processing %s (comp=%d, season=%d)", comp_label, comp_id, season_id)
        try:
            matches_df = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as exc:
            logger.warning("Failed to get matches for %s: %s", comp_label, exc)
            continue

        arg_matches = matches_df[
            matches_df["home_team"].astype(str).str.contains("Argentina", na=False)
            | matches_df["away_team"].astype(str).str.contains("Argentina", na=False)
        ]

        logger.info("  %d Argentina matches found", len(arg_matches))

        for _, m in arg_matches.iterrows():
            mid = int(m["match_id"])
            date = str(m.get("match_date", ""))[:10]
            opp = _opponent_name(m)
            logger.info("  Aggregating events: match_id=%d  %s (%s)", mid, opp, date)
            rows = _aggregate_match(sb, mid, date, opp, comp_label)
            all_rows.extend(rows)

    if not all_rows:
        logger.warning("No player NT stats collected")
        return pd.DataFrame(), pd.DataFrame()

    df_all = pd.DataFrame(all_rows)
    logger.info("Total player-match rows: %d", len(df_all))

    # Split outfield vs GK
    gk_mask = df_all["player_name"].apply(
        lambda n: normalize_name(str(n)) in GK_NAMES_NORM
    )
    df_outfield = df_all[~gk_mask].reset_index(drop=True)
    df_gk = df_all[gk_mask].reset_index(drop=True)

    return df_outfield, df_gk


def save_outfield(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE_OUTFIELD, index=False, encoding="utf-8")
    logger.info("Saved outfield stats (%d rows) → %s", len(df), OUT_FILE_OUTFIELD)


def save_gk(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE_GK, index=False, encoding="utf-8")
    logger.info("Saved GK stats (%d rows) → %s", len(df), OUT_FILE_GK)


if __name__ == "__main__":
    df_out, df_gk = _run_extraction()
    save_outfield(df_out)
    save_gk(df_gk)
    logger.info("Done.")
