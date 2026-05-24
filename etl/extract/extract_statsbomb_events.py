"""
etl/extract/extract_statsbomb_events.py
-----------------------------------------
Downloads Argentina match event data from StatsBomb Open Data.

Targets:
  - FIFA World Cup 2022      (competition_id=43,  season_id=106)
  - Copa América 2021        (competition_id=223, season_id=282)

These IDs are verified dynamically from sb.competitions() at runtime.

Outputs:
  data/raw/statsbomb/argentina_events.csv
  data/raw/statsbomb/argentina_statsbomb_matches.csv
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import normalize_name  # noqa: E402
from config.players import SQUAD  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "statsbomb"
OUT_EVENTS = OUT_DIR / "argentina_events.csv"
OUT_MATCHES = OUT_DIR / "argentina_statsbomb_matches.csv"

# Competitions to target (name matching — IDs confirmed dynamically)
TARGET_COMPETITIONS = [
    {"competition_name": "FIFA World Cup",  "season_name": "2022"},
    {"competition_name": "Copa America",    "season_name": "2024"},
    # Also try common alternate spellings
    {"competition_name": "Copa América",    "season_name": "2024"},
]

# Rate limit between match event requests
EVENT_PAUSE_SECONDS = 2.0

# Precomputed squad name set for fast filtering
SQUAD_NAMES_NORM: set[str] = {normalize_name(p["player_name"]) for p in SQUAD}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_match_fbref_id(date_str: str, opponent: str) -> str:
    """Mirrors the match_id format used in extract_fbref_matches.py."""
    date_part = str(date_str).replace("-", "")
    opp_part = str(opponent).replace(" ", "_")[:10]
    return f"ARG_{date_part}_{opp_part}"


def _opponent_from_match(row: pd.Series) -> str:
    """Return the non-Argentina team name for a match row."""
    home = str(row.get("home_team", ""))
    away = str(row.get("away_team", ""))
    return away if "Argentina" in home else home


def _safe_location(loc: Any, idx: int) -> Optional[float]:
    """Safely extract x or y from a StatsBomb location list."""
    try:
        if isinstance(loc, list) and len(loc) > idx:
            return float(loc[idx])
    except (TypeError, ValueError):
        pass
    return None


def _parse_event_row(event: Dict) -> Dict:
    """Flatten one StatsBomb event dict to a flat row for CSV output."""
    location = event.get("location")
    end_location = event.get("pass", {}).get("end_location") if isinstance(event.get("pass"), dict) else None

    # Outcome: varies by event type — check pass, shot, dribble, etc.
    outcome = None
    for key in ("pass", "shot", "dribble", "carry", "clearance", "foul_committed"):
        sub = event.get(key)
        if isinstance(sub, dict):
            outcome_dict = sub.get("outcome")
            if isinstance(outcome_dict, dict):
                outcome = outcome_dict.get("name")
            elif outcome_dict is not None:
                outcome = str(outcome_dict)
            break

    player = event.get("player")
    player_name = player.get("name", "") if isinstance(player, dict) else str(player or "")

    event_type = event.get("type")
    event_type_name = event_type.get("name", "") if isinstance(event_type, dict) else str(event_type or "")

    return {
        "event_id":      event.get("id"),
        "event_type":    event_type_name,
        "period":        event.get("period"),
        "minute":        event.get("minute"),
        "second":        event.get("second"),
        "player_name":   player_name,
        "x":             _safe_location(location, 0),
        "y":             _safe_location(location, 1),
        "end_x":         _safe_location(end_location, 0),
        "end_y":         _safe_location(end_location, 1),
        "outcome":       outcome,
    }


# ---------------------------------------------------------------------------
# Competition discovery
# ---------------------------------------------------------------------------

def _find_target_competitions(competitions_df: pd.DataFrame) -> list[Dict]:
    """
    Match the competitions DataFrame against our TARGET_COMPETITIONS list.
    Returns a list of dicts with competition_id, season_id, competition_name, season_name.
    """
    found: list[Dict] = []
    seen_ids: set[tuple] = set()

    for target in TARGET_COMPETITIONS:
        mask = (
            competitions_df["competition_name"].str.strip().str.lower()
            == target["competition_name"].strip().lower()
        ) & (
            competitions_df["season_name"].astype(str).str.strip()
            == target["season_name"].strip()
        )
        matches = competitions_df[mask]
        if matches.empty:
            logger.debug(
                "Target competition not found: %s %s",
                target["competition_name"],
                target["season_name"],
            )
            continue
        for _, row in matches.iterrows():
            key = (int(row["competition_id"]), int(row["season_id"]))
            if key not in seen_ids:
                seen_ids.add(key)
                found.append(
                    {
                        "competition_id":   int(row["competition_id"]),
                        "season_id":        int(row["season_id"]),
                        "competition_name": row["competition_name"],
                        "season_name":      row["season_name"],
                    }
                )
                logger.info(
                    "Found competition: %s %s (comp_id=%d, season_id=%d)",
                    row["competition_name"],
                    row["season_name"],
                    key[0],
                    key[1],
                )

    return found


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_statsbomb_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        from statsbombpy import sb
    except ImportError:
        logger.error("statsbombpy is not installed. Run: pip install statsbombpy")
        return pd.DataFrame(), pd.DataFrame()

    # 1. Discover available competitions
    logger.info("Fetching StatsBomb competition list…")
    try:
        competitions_df = sb.competitions()
    except Exception as exc:
        logger.error("Failed to fetch competitions: %s", exc)
        return pd.DataFrame(), pd.DataFrame()

    target_comps = _find_target_competitions(competitions_df)
    if not target_comps:
        logger.error(
            "None of the target competitions were found in StatsBomb open data. "
            "Available competitions:\n%s",
            competitions_df[["competition_name", "season_name"]].drop_duplicates().to_string(),
        )
        return pd.DataFrame(), pd.DataFrame()

    all_events: list[pd.DataFrame] = []
    all_matches_rows: list[Dict] = []

    for comp in target_comps:
        comp_id = comp["competition_id"]
        season_id = comp["season_id"]
        comp_name = comp["competition_name"]
        season_name = comp["season_name"]

        # 2. Get matches for this competition
        logger.info("Fetching matches for %s %s…", comp_name, season_name)
        try:
            matches_df = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as exc:
            logger.warning("Failed to get matches for comp_id=%d: %s", comp_id, exc)
            continue

        # Filter to Argentina matches
        arg_matches = matches_df[
            matches_df["home_team"].str.contains("Argentina", na=False)
            | matches_df["away_team"].str.contains("Argentina", na=False)
        ].copy()

        logger.info(
            "  %s %s — %d Argentina matches found",
            comp_name, season_name, len(arg_matches),
        )

        for _, match_row in arg_matches.iterrows():
            match_id = int(match_row["match_id"])
            match_date = str(match_row.get("match_date", ""))
            home_team = str(match_row.get("home_team", ""))
            away_team = str(match_row.get("away_team", ""))
            home_score = match_row.get("home_score")
            away_score = match_row.get("away_score")
            opponent = _opponent_from_match(match_row)

            # Record match summary
            all_matches_rows.append(
                {
                    "statsbomb_match_id": match_id,
                    "date":               match_date,
                    "competition":        comp_name,
                    "season":             season_name,
                    "home_team":          home_team,
                    "away_team":          away_team,
                    "home_score":         home_score,
                    "away_score":         away_score,
                    "match_fbref_id":     _build_match_fbref_id(match_date, opponent),
                }
            )

            # 3. Fetch events for this match
            logger.info(
                "  Fetching events: match_id=%d  %s vs %s (%s)",
                match_id, home_team, away_team, match_date,
            )
            time.sleep(EVENT_PAUSE_SECONDS)

            try:
                events = sb.events(match_id=match_id)
            except Exception as exc:
                logger.warning(
                    "  Failed to fetch events for match_id=%d: %s", match_id, exc
                )
                continue

            if events is None or (isinstance(events, pd.DataFrame) and events.empty):
                logger.warning("  No events returned for match_id=%d", match_id)
                continue

            # Handle both DataFrame and dict responses
            if isinstance(events, dict):
                try:
                    events = pd.DataFrame(events.values())
                except Exception:
                    logger.warning(
                        "  Could not convert events dict to DataFrame for match_id=%d",
                        match_id,
                    )
                    continue

            # Parse each event row
            parsed_rows: list[Dict] = []
            for _, ev in events.iterrows():
                try:
                    row = _parse_event_row(ev.to_dict())
                    # Only keep events where the player is in our squad
                    if normalize_name(row["player_name"]) in SQUAD_NAMES_NORM:
                        row["statsbomb_match_id"] = match_id
                        row["match_fbref_id"] = _build_match_fbref_id(match_date, opponent)
                        row["competition"] = comp_name
                        row["season"] = season_name
                        row["date"] = match_date
                        parsed_rows.append(row)
                except Exception as exc:
                    logger.debug("  Skipping event parse error: %s", exc)
                    continue

            if parsed_rows:
                all_events.append(pd.DataFrame(parsed_rows))
                logger.info(
                    "  match_id=%d — kept %d events for squad players",
                    match_id, len(parsed_rows),
                )

    # 4. Combine
    if all_events:
        events_df = pd.concat(all_events, ignore_index=True)
    else:
        logger.warning("No events collected.")
        events_df = pd.DataFrame(
            columns=[
                "event_id", "event_type", "period", "minute", "second",
                "player_name", "x", "y", "end_x", "end_y", "outcome",
                "statsbomb_match_id", "match_fbref_id",
                "competition", "season", "date",
            ]
        )

    matches_summary_df = pd.DataFrame(all_matches_rows) if all_matches_rows else pd.DataFrame(
        columns=[
            "statsbomb_match_id", "date", "competition", "season",
            "home_team", "away_team", "home_score", "away_score", "match_fbref_id",
        ]
    )

    logger.info(
        "Total events collected: %d | Matches summarised: %d",
        len(events_df), len(matches_summary_df),
    )
    return events_df, matches_summary_df


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save(events_df: pd.DataFrame, matches_df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    events_df.to_csv(OUT_EVENTS, index=False, encoding="utf-8")
    logger.info("Saved %d events → %s", len(events_df), OUT_EVENTS)
    matches_df.to_csv(OUT_MATCHES, index=False, encoding="utf-8")
    logger.info("Saved %d match summaries → %s", len(matches_df), OUT_MATCHES)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    events_df, matches_df = extract_statsbomb_events()
    save(events_df, matches_df)
