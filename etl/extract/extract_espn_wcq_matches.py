"""
etl/extract/extract_espn_wcq_matches.py
----------------------------------------
Extracts Argentina CONMEBOL WCQ 2026 match data from ESPN unofficial API.

Produces two CSVs:
  data/raw/wcq_matches.csv        — one row per match (fact_match)
  data/raw/wcq_player_matches.csv — one row per player per match (fact_player_match)

What ESPN provides for WCQ:
  fact_match       : date, opponent, home_away, goals_for, goals_against, venue
  fact_player_match: started, minutes_played (derived), goals, yellow_cards, red_cards

What ESPN does NOT provide: assists, shots, xg, passes, tackles, saves.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import normalize_name
from config.players import SQUAD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_MATCHES  = OUT_DIR / "wcq_matches.csv"
OUT_PLAYERS  = OUT_DIR / "wcq_player_matches.csv"

SLUG         = "fifa.worldq.conmebol"
BASE         = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{SLUG}"
ARG_NAME     = "Argentina"
COMPETITION_ID = 4  # World Cup Qualifying - CONMEBOL (from dim_competition)

# Months to scan — all WCQ 2026 rounds
WCQ_MONTHS = [
    "202309", "202310", "202311",  # Round 1–6  (2023)
    "202403", "202406",             # Round 7–10 (2024 friendlies window)
    "202409", "202410", "202411",  # Round 7–12 (2024)
    "202503", "202506",             # Round 13–16 (2025)
    "202509", "202510", "202511",  # Round 17–18 (2025)
]

# ESPN event types we care about
TYPE_GOAL         = {"goal", "goal---free-kick", "goal---penalty", "goal---own-goal",
                     "goal---header", "goal---open-play"}
TYPE_SUBSTITUTION = {"substitution"}
TYPE_YELLOW       = {"yellow-card"}
TYPE_RED          = {"red-card", "red-card---second-yellow"}

# Squad normalized names → player_name for matching
SQUAD_NORM = {normalize_name(p["player_name"]): p["player_name"] for p in SQUAD}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

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

def _get(url: str, pause: float = 2.0) -> Optional[dict]:
    time.sleep(pause)
    try:
        r = _session().get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.debug("GET failed %s — %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Step 1: collect all Argentina WCQ event IDs
# ---------------------------------------------------------------------------

def _fetch_event_ids() -> list[dict]:
    """Return list of ESPN event dicts for Argentina WCQ matches."""
    events = []
    seen = set()
    for ym in WCQ_MONTHS:
        data = _get(f"{BASE}/scoreboard?dates={ym}", pause=1.5)
        if not data:
            continue
        for ev in data.get("events", []):
            if ARG_NAME not in ev.get("name", ""):
                continue
            eid = ev["id"]
            if eid in seen:
                continue
            seen.add(eid)
            comp = ev.get("competitions", [{}])[0]
            completed = comp.get("status", {}).get("type", {}).get("completed", False)
            if completed:
                events.append(ev)
    logger.info("Found %d completed Argentina WCQ events", len(events))
    return events


# ---------------------------------------------------------------------------
# Step 2: parse one match summary
# ---------------------------------------------------------------------------

def _parse_match(event: dict) -> tuple[Optional[dict], list[dict]]:
    """
    Fetch and parse one match summary.
    Returns (match_row, [player_match_rows]).
    """
    eid = event["id"]
    summary = _get(f"{BASE}/summary?event={eid}")
    if not summary:
        logger.warning("No summary for event %s", eid)
        return None, []

    # ── Match-level data ────────────────────────────────────────────────────
    header = summary.get("header", {})
    comp   = (header.get("competitions") or [{}])[0]
    competitors = comp.get("competitors", [])

    arg_comp  = next((c for c in competitors if c.get("team",{}).get("displayName") == ARG_NAME), None)
    opp_comp  = next((c for c in competitors if c.get("team",{}).get("displayName") != ARG_NAME), None)

    if not arg_comp or not opp_comp:
        logger.warning("Cannot identify Argentina/opponent in event %s", eid)
        return None, []

    goals_for     = int(arg_comp.get("score") or 0)
    goals_against = int(opp_comp.get("score") or 0)
    home_away     = arg_comp.get("homeAway", "neutral")
    opponent      = opp_comp.get("team", {}).get("displayName", "Unknown")

    game_info = summary.get("gameInfo", {})
    venue     = game_info.get("venue", {}).get("fullName", None) if game_info else None

    date_str = event.get("date", "")[:10]

    match_row = {
        "match_id":       f"wcq_{eid}",
        "date":           date_str,
        "competition_id": COMPETITION_ID,
        "opponent":       opponent,
        "home_away":      home_away,
        "goals_for":      goals_for,
        "goals_against":  goals_against,
        "venue":          venue,
    }

    # ── Parse keyEvents for goals/subs/cards ───────────────────────────────
    key_events = summary.get("keyEvents", [])

    goals_by_athlete:        dict[str, int]   = {}
    yellow_by_athlete:       dict[str, int]   = {}
    red_by_athlete:          dict[str, int]   = {}
    sub_in_minute:           dict[str, int]   = {}  # athlete_id → minute entered
    sub_out_minute:          dict[str, int]   = {}  # athlete_id → minute left

    for ke in key_events:
        etype = ke.get("type", {}).get("type", "")
        team_name = ke.get("team", {}).get("displayName", "")
        if team_name != ARG_NAME:
            continue  # only track Argentina events

        # clock.value is in seconds since match start
        clock_sec = ke.get("clock", {}).get("value", 0) or 0
        minute    = max(1, int(clock_sec / 60))

        participants = ke.get("participants", [])

        if etype in TYPE_GOAL:
            for p in participants:
                aid = p.get("athlete", {}).get("id", "")
                if aid:
                    goals_by_athlete[aid] = goals_by_athlete.get(aid, 0) + 1

        elif etype in TYPE_SUBSTITUTION and len(participants) >= 2:
            in_id  = participants[0].get("athlete", {}).get("id", "")   # came on
            out_id = participants[1].get("athlete", {}).get("id", "")   # went off
            if in_id:
                sub_in_minute[in_id]  = minute
            if out_id:
                sub_out_minute[out_id] = minute

        elif etype in TYPE_YELLOW:
            for p in participants:
                aid = p.get("athlete", {}).get("id", "")
                if aid:
                    yellow_by_athlete[aid] = yellow_by_athlete.get(aid, 0) + 1

        elif etype in TYPE_RED:
            for p in participants:
                aid = p.get("athlete", {}).get("id", "")
                if aid:
                    red_by_athlete[aid] = red_by_athlete.get(aid, 0) + 1

    # ── Build player rows from Argentina roster ────────────────────────────
    player_rows = []
    rosters = summary.get("rosters", [])
    arg_roster = next(
        (r for r in rosters if r.get("team", {}).get("displayName") == ARG_NAME),
        None
    )
    if not arg_roster:
        logger.warning("No Argentina roster in event %s", eid)
        return match_row, []

    for entry in arg_roster.get("roster", []):
        athlete    = entry.get("athlete", {})
        aid        = athlete.get("id", "")
        name_raw   = athlete.get("displayName", "")
        started    = entry.get("starter", False)
        subbed_in  = entry.get("subbedIn", False)
        subbed_out = entry.get("subbedOut", False)
        dnp        = entry.get("didNotPlay", False)

        if dnp:
            continue  # did not play — skip

        # Only include squad players
        norm = normalize_name(name_raw)
        squad_name = SQUAD_NORM.get(norm)
        if squad_name is None:
            # Try last-name fallback
            last = norm.split()[-1] if norm.split() else ""
            matches = {k: v for k, v in SQUAD_NORM.items() if last and k.endswith(last)}
            if len(matches) == 1:
                squad_name = list(matches.values())[0]
        if squad_name is None:
            continue  # player not in our squad — skip

        # Derive minutes played
        if started:
            sub_out = sub_out_minute.get(aid)
            minutes = sub_out if sub_out else 90
        elif subbed_in:
            sub_in = sub_in_minute.get(aid)
            minutes = (90 - sub_in) if sub_in else None
        else:
            minutes = None  # unknown

        player_rows.append({
            "match_id":      f"wcq_{eid}",
            "player_name":   squad_name,
            "started":       started,
            "minutes_played": minutes,
            "goals":         goals_by_athlete.get(aid, 0),
            "yellow_cards":  yellow_by_athlete.get(aid, 0),
            "red_cards":     red_by_athlete.get(aid, 0),
        })

    return match_row, player_rows


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract() -> tuple[pd.DataFrame, pd.DataFrame]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    events = _fetch_event_ids()
    if not events:
        logger.error("No events found — check slug and month range")
        return pd.DataFrame(), pd.DataFrame()

    all_matches: list[dict] = []
    all_players: list[dict] = []

    for ev in events:
        match_row, player_rows = _parse_match(ev)
        if match_row:
            all_matches.append(match_row)
            all_players.extend(player_rows)
            logger.info(
                "  %s | %s %s-%s | %d squad players",
                match_row["date"], match_row["opponent"],
                match_row["goals_for"], match_row["goals_against"],
                len(player_rows),
            )

    df_matches  = pd.DataFrame(all_matches)
    df_players  = pd.DataFrame(all_players)

    df_matches.to_csv(OUT_MATCHES,  index=False, encoding="utf-8")
    df_players.to_csv(OUT_PLAYERS,  index=False, encoding="utf-8")

    logger.info("Saved %d matches to %s",  len(df_matches),  OUT_MATCHES)
    logger.info("Saved %d player rows to %s", len(df_players), OUT_PLAYERS)
    return df_matches, df_players


if __name__ == "__main__":
    extract()
