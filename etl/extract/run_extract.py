"""
etl/extract/run_extract.py
---------------------------
Orchestrator that runs all four extract steps in sequence.

Steps
-----
1. extract_fbref_matches        → data/raw/fbref/argentina_matches.csv
2. extract_fbref_player_nt_stats→ data/raw/fbref/argentina_player_match_stats.csv
                                  data/raw/fbref/argentina_gk_match_stats.csv
3. extract_fbref_club_stats     → data/raw/fbref/club_stats_all_leagues.csv
4. extract_statsbomb_events     → data/raw/statsbomb/argentina_events.csv
                                  data/raw/statsbomb/argentina_statsbomb_matches.csv

Each step is wrapped in try/except — a failure logs the error and continues
to the next step. Timing is logged for each step.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_extract")


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------

def _run_step(step_name: str, fn, *args, **kwargs):
    """Execute fn(*args, **kwargs), log timing, swallow exceptions."""
    logger.info("=" * 60)
    logger.info("STEP START: %s  [%s]", step_name, datetime.now().strftime("%H:%M:%S"))
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.info(
            "STEP OK:    %s  (%.1f s)", step_name, elapsed
        )
        return result
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error(
            "STEP FAIL:  %s  (%.1f s) — %s: %s",
            step_name, elapsed, type(exc).__name__, exc,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Individual step wrappers
# ---------------------------------------------------------------------------

def step_fbref_matches():
    from etl.extract.extract_fbref_matches import extract_argentina_matches, save
    df = extract_argentina_matches()
    save(df)
    return df


def step_fbref_player_nt_stats():
    from etl.extract.extract_fbref_player_nt_stats import (
        extract_outfield_stats,
        extract_gk_stats,
        save_outfield,
        save_gk,
    )
    from etl.extract.utils import get_session
    session = get_session()
    df_outfield = extract_outfield_stats(session)
    save_outfield(df_outfield)
    df_gk = extract_gk_stats(session)
    save_gk(df_gk)
    return df_outfield, df_gk


def step_fbref_club_stats():
    from etl.extract.extract_fbref_club_stats import extract_club_stats, save
    df = extract_club_stats()
    save(df)
    return df


def step_statsbomb_events():
    from etl.extract.extract_statsbomb_events import extract_statsbomb_events, save
    events_df, matches_df = extract_statsbomb_events()
    save(events_df, matches_df)
    return events_df, matches_df


def step_sofascore_big5_supplement():
    from etl.extract.sofascore_big5_supplement import extract_big5_supplement, save
    df = extract_big5_supplement()
    save(df)
    return df


def step_sofascore_nt_match_stats():
    from etl.extract.extract_sofascore_nt_match_stats import extract_sofascore_nt_stats, save
    df = extract_sofascore_nt_stats()
    save(df)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    pipeline_start = time.perf_counter()
    logger.info("=" * 60)
    logger.info("PIPELINE START — Argentina 2026 Extract")
    logger.info("Project root: %s", PROJECT_ROOT)
    logger.info("=" * 60)

    _run_step("1/6 — FBRef Argentina Matches",              step_fbref_matches)
    _run_step("2/6 — FBRef Player NT Stats (StatsBomb)",    step_fbref_player_nt_stats)
    _run_step("3/6 — FBRef Club Stats (Understat/Sofascore)",step_fbref_club_stats)
    _run_step("4/6 — StatsBomb Events",                     step_statsbomb_events)
    _run_step("5/6 — Sofascore Big5 Supplement Stats",      step_sofascore_big5_supplement)
    _run_step("6/6 — Sofascore NT Match Stats (CA2021+WCQ)",step_sofascore_nt_match_stats)

    elapsed = time.perf_counter() - pipeline_start
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — total time %.1f s", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
