"""
etl/transform/transform_player_match_from_events.py
------------------------------------------------------
Derives fact_player_match rows for Copa América 2024 and WC 2022
by aggregating event_statsbomb per (match_id, player_id).

Also derives xg_for / xg_against for fact_match from Shot events.

Aggregations from event_statsbomb:
  goals             — Shot events where outcome = 'Goal'
  shots             — all Shot events
  shots_on_target   — Shot where outcome IN ('Goal','Saved','Saved to Post','Saved Off Target')
  xg                — SUM(xg) on Shot events
  passes_completed  — Pass events where outcome IS NULL (StatsBomb NULL = success)
  passes_attempted  — all Pass events
  pass_pct          — passes_completed / passes_attempted * 100
  tackles           — Interception events (closest proxy available)
  interceptions     — Interception events
  started           — player has events in period 1
  minutes_played    — derived: max(minute) of own events
                      (approximation; substitution data would be more precise)

Writes to:
  data/transformed/fact_match.csv        (updates xg_for / xg_against)
  data/transformed/fact_player_match.csv (appends Copa/WC rows)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

TRANSFORMED_DIR   = PROJECT_ROOT / "data" / "transformed"
EVENTS_CSV        = TRANSFORMED_DIR / "events_statsbomb.csv"
DIM_PLAYER_CSV    = TRANSFORMED_DIR / "dim_player.csv"
FACT_MATCH_CSV    = TRANSFORMED_DIR / "fact_match.csv"
FACT_PM_CSV       = TRANSFORMED_DIR / "fact_player_match.csv"

# Shot outcomes that count as "on target"
ON_TARGET = {"Goal", "Saved", "Saved to Post", "Saved Off Target", "Saved To Post"}

# All columns the fact_player_match loader expects
_ALL_COLS = [
    "match_id", "player_id", "started", "minutes_played",
    "goals", "assists", "shots", "shots_on_target",
    "xg", "xag",
    "passes_completed", "passes_attempted", "pass_pct",
    "progressive_passes", "key_passes", "progressive_carries",
    "tackles", "interceptions", "blocks",
    "yellow_cards", "red_cards",
    "saves", "save_pct", "clean_sheet", "psxg",
]


def transform() -> tuple[pd.DataFrame, pd.DataFrame]:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not EVENTS_CSV.exists():
        logger.error("Missing %s — run extract_statsbomb_events first", EVENTS_CSV)
        return pd.DataFrame(), pd.DataFrame()

    events = pd.read_csv(EVENTS_CSV, encoding="utf-8", low_memory=False)
    dim    = pd.read_csv(DIM_PLAYER_CSV, encoding="utf-8")
    fm     = pd.read_csv(FACT_MATCH_CSV, encoding="utf-8")

    pid_to_name = dict(zip(dim["player_id"], dim["player_name"]))

    # ── Task C: xg_for / xg_against per match ──────────────────────────────
    shots = events[events["event_type"] == "Shot"].copy()
    shots["xg"] = pd.to_numeric(shots["xg"], errors="coerce")

    arg_player_ids = set(dim["player_id"])

    xg_by_match = (
        shots[shots["player_id"].isin(arg_player_ids)]
        .groupby("match_id")["xg"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"xg": "_xg_for"})
    )
    fm = fm.merge(xg_by_match, on="match_id", how="left")
    null_mask = fm["xg_for"].isna() & fm["_xg_for"].notna()
    fm.loc[null_mask, "xg_for"] = fm.loc[null_mask, "_xg_for"]
    fm.drop(columns=["_xg_for"], inplace=True)

    fm.to_csv(FACT_MATCH_CSV, index=False, encoding="utf-8")
    logger.info("Updated xg_for for %d matches in fact_match", null_mask.sum())

    # ── Task A: fact_player_match rows from events ──────────────────────────
    # Copa/WC match_ids already in events (match_fbref_id format ARG_YYYYMMDD_Opponent)
    copa_wc_matches = set(fm[fm["competition_id"].isin([2, 3])]["match_id"])
    ev = events[events["match_id"].isin(copa_wc_matches)].copy()

    if ev.empty:
        logger.warning("No events found for Copa/WC matches")
        return fm, pd.DataFrame()

    rows = []
    for (match_id, player_id), grp in ev.groupby(["match_id", "player_id"]):
        if player_id not in arg_player_ids:
            continue

        # Started: appeared in period 1
        started = bool((grp["period"] == 1).any())

        # Minutes: use max event minute as approximation
        minutes = int(grp["minute"].max()) if grp["minute"].notna().any() else None

        # Shots
        shot_grp = grp[grp["event_type"] == "Shot"]
        goals_n           = int((shot_grp["outcome"] == "Goal").sum())
        shots_n           = len(shot_grp)
        shots_on_target_n = int(shot_grp["outcome"].isin(ON_TARGET).sum())
        xg_val            = shot_grp["xg"].sum() if len(shot_grp) > 0 else None
        xg_val            = round(float(xg_val), 3) if xg_val is not None and xg_val > 0 else None

        # Passes
        pass_grp     = grp[grp["event_type"] == "Pass"]
        passes_att   = len(pass_grp)
        # StatsBomb: NULL outcome = successful pass
        passes_comp  = int(pass_grp["outcome"].isna().sum())
        pass_pct_val = round(passes_comp / passes_att * 100, 1) if passes_att > 0 else None

        # Interceptions (best proxy for tackles in current schema)
        intercept_grp = grp[grp["event_type"] == "Interception"]
        interceptions_n = len(intercept_grp)

        # Saves (GK-specific)
        gk_grp  = grp[grp["event_type"] == "Goal Keeper"]
        saves_n = int((gk_grp["outcome"].isin({"Saved", "Saved To Post", "Claim", "Touched Out"})).sum()) if len(gk_grp) > 0 else None

        rows.append({
            "match_id":         match_id,
            "player_id":        int(player_id),
            "started":          started,
            "minutes_played":   minutes,
            "goals":            goals_n,
            "assists":          None,       # not derivable from event_statsbomb
            "shots":            shots_n,
            "shots_on_target":  shots_on_target_n,
            "xg":               xg_val,
            "xag":              None,
            "passes_completed": passes_comp,
            "passes_attempted": passes_att,
            "pass_pct":         pass_pct_val,
            "progressive_passes": None,
            "key_passes":       None,
            "progressive_carries": None,
            "tackles":          None,       # Duel sub-types not in current schema
            "interceptions":    interceptions_n,
            "blocks":           None,
            "yellow_cards":     None,
            "red_cards":        None,
            "saves":            saves_n,
            "save_pct":         None,
            "clean_sheet":      None,
            "psxg":             None,
        })

    df_copa_wc = pd.DataFrame(rows)
    logger.info(
        "Derived %d fact_player_match rows from events (Copa/WC, %d matches)",
        len(df_copa_wc), df_copa_wc["match_id"].nunique() if not df_copa_wc.empty else 0,
    )

    # Append to existing fact_player_match (WCQ rows stay intact)
    if FACT_PM_CSV.exists():
        existing = pd.read_csv(FACT_PM_CSV, encoding="utf-8")
        # Remove any existing Copa/WC rows to avoid dupes on re-run
        existing = existing[~existing["match_id"].isin(copa_wc_matches)]
        combined = pd.concat([existing, df_copa_wc], ignore_index=True)
    else:
        combined = df_copa_wc

    for col in _ALL_COLS:
        if col not in combined.columns:
            combined[col] = None
    combined = combined[_ALL_COLS]

    combined.to_csv(FACT_PM_CSV, index=False, encoding="utf-8")
    logger.info("fact_player_match: %d total rows -> %s", len(combined), FACT_PM_CSV)
    return fm, combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    transform()
