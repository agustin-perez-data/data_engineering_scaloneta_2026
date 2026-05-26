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


_NORM_TO_CANONICAL: dict[str, str] = {
    normalize_name(p["player_name"]): p["player_name"] for p in SQUAD
}


def _match_squad_norm(sb_name: str) -> str | None:
    """Match a StatsBomb full name (e.g. 'Lionel Andrés Messi Cuccittini')
    to the canonical normalized SQUAD name ('lionel messi') using word-subset
    matching: the SQUAD name words must all appear in the StatsBomb name."""
    norm = normalize_name(sb_name)
    if norm in SQUAD_NAMES_NORM:
        return norm
    sb_words = set(norm.split())
    for sq_norm in SQUAD_NAMES_NORM:
        if set(sq_norm.split()).issubset(sb_words):
            return sq_norm
    return None


def _canonical_name(sb_name: str) -> str:
    """Return the canonical SQUAD player_name for a StatsBomb full name."""
    norm = _match_squad_norm(sb_name)
    return _NORM_TO_CANONICAL.get(norm, sb_name) if norm else sb_name

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

def _safe_pid(val) -> int | None:
    """Convert a player_id value to int, returning None if NaN/None."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _aggregate_match(sb, match_id: int, match_date: str, opponent: str, comp: str) -> list[dict]:
    """Return list of player-stat dicts for one Argentina match.

    StatsBomb returns a flattened DataFrame — fields like shot_statsbomb_xg,
    pass_outcome, goalkeeper_outcome etc. are top-level columns, not nested dicts.
    """
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

    # Build player registry from lineup (player_id + player_name only; position from tactics)
    players: dict[int, dict] = {}
    for _, p in arg_lineup.iterrows():
        pid = _safe_pid(p.get("player_id"))
        if pid is None:
            continue
        players[pid] = {
            "player_name": p.get("player_name", ""),
            "position": "",
            "started": False,
            "minutes_played": 0,
            "goals": 0, "assists": 0,
            "shots": 0, "shots_on_target": 0,
            "xg": 0.0, "xag": 0.0,
            "passes_completed": 0, "passes_attempted": 0,
            "key_passes": 0, "progressive_passes": 0,
            "tackles": 0, "interceptions": 0, "blocks": 0,
            "yellow_cards": 0, "red_cards": 0,
            "saves": 0, "goals_against_gk": 0, "clean_sheet": False,
        }

    # Filter Argentina events once (type/team are plain strings in flattened format)
    arg_mask = events_df["team"] == "Argentina"
    arg_events = events_df[arg_mask]

    # Starting XI — position + mark starters
    for _, ev in arg_events[arg_events["type"] == "Starting XI"].iterrows():
        tactics = ev.get("tactics")
        if not isinstance(tactics, dict):
            continue
        for li in tactics.get("lineup", []):
            lp_id = _safe_pid(_get_nested(li, "player", "id"))
            pos = _get_nested(li, "position", "name") or ""
            if lp_id and lp_id in players:
                players[lp_id]["started"] = True
                players[lp_id]["minutes_played"] = 90
                players[lp_id]["position"] = pos

    # Substitutions — actual minutes
    for _, ev in arg_events[arg_events["type"] == "Substitution"].iterrows():
        minute = int(ev.get("minute") or 0)
        pid_off = _safe_pid(ev.get("player_id"))
        pid_on = _safe_pid(ev.get("substitution_replacement_id"))
        if pid_off and pid_off in players:
            players[pid_off]["minutes_played"] = minute
        if pid_on and pid_on in players:
            players[pid_on]["minutes_played"] = 90 - minute

    # Defaults for players whose minutes weren't set
    for info in players.values():
        if info["started"] and info["minutes_played"] == 0:
            info["minutes_played"] = 90
        elif not info["started"] and info["minutes_played"] == 0:
            info["minutes_played"] = 30

    # Aggregate stats from Argentina events
    for _, ev in arg_events.iterrows():
        pid = _safe_pid(ev.get("player_id"))
        if pid is None or pid not in players:
            continue
        etype = ev.get("type", "")

        if etype == "Shot":
            players[pid]["shots"] += 1
            xg = float(ev.get("shot_statsbomb_xg") or 0)
            players[pid]["xg"] += xg
            outcome = str(ev.get("shot_outcome") or "")
            if outcome == "Goal":
                players[pid]["goals"] += 1
                players[pid]["shots_on_target"] += 1
            elif "Saved" in outcome:
                players[pid]["shots_on_target"] += 1

        elif etype == "Pass":
            players[pid]["passes_attempted"] += 1
            # pass_outcome is NaN when completed, string when incomplete
            outcome = ev.get("pass_outcome")
            if outcome is None or (isinstance(outcome, float) and pd.isna(outcome)):
                players[pid]["passes_completed"] += 1
            if ev.get("pass_goal_assist") is True:
                players[pid]["assists"] += 1
            if ev.get("pass_shot_assist") is True:
                players[pid]["key_passes"] += 1

        elif etype == "Duel":
            if str(ev.get("duel_type") or "").lower() == "tackle":
                players[pid]["tackles"] += 1

        elif etype == "Interception":
            players[pid]["interceptions"] += 1

        elif etype == "Block":
            players[pid]["blocks"] += 1

        elif etype == "Goal Keeper":
            outcome = str(ev.get("goalkeeper_outcome") or "")
            if "Saved" in outcome or "Touched" in outcome:
                players[pid]["saves"] += 1

        elif etype == "Foul Committed":
            card = str(ev.get("foul_committed_card") or "")
            if "Yellow" in card:
                players[pid]["yellow_cards"] += 1
            elif "Red" in card:
                players[pid]["red_cards"] += 1

        elif etype == "Bad Behaviour":
            card = str(ev.get("bad_behaviour_card") or "")
            if "Yellow" in card:
                players[pid]["yellow_cards"] += 1
            elif "Red" in card:
                players[pid]["red_cards"] += 1

    # Goals conceded (for GK clean sheet)
    opp_shots = events_df[
        (events_df["type"] == "Shot") & (events_df["team"] != "Argentina")
    ]
    goals_conceded = (opp_shots["shot_outcome"] == "Goal").sum()

    fbref_mid = _build_match_id(match_date, opponent)

    rows = []
    for pid, info in players.items():
        norm = _match_squad_norm(info["player_name"])
        if norm is None:
            continue

        is_gk = norm in GK_NAMES_NORM
        if is_gk:
            info["clean_sheet"] = goals_conceded == 0
            info["goals_against_gk"] = goals_conceded

        rows.append({
            "match_id": fbref_mid,
            "player_name": _canonical_name(info["player_name"]),
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
        lambda n: (_match_squad_norm(str(n)) or "") in GK_NAMES_NORM
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
