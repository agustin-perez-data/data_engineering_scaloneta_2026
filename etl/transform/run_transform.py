"""
etl/transform/run_transform.py
--------------------------------
Orchestrator that executes all transform steps in dependency order:

    1. dim_player
    2. dim_competition
    3. fact_match
    4. fact_player_match
    5. fact_player_club_season
    6. events_statsbomb

Each step is wrapped in a try/except so a failure in one step is logged
but does not prevent subsequent (independent) steps from running.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_transform")


def _run_step(name: str, func) -> bool:
    """Execute a transform function, log result, return True on success."""
    logger.info("=== START: %s ===", name)
    t0 = time.perf_counter()
    try:
        func()
        elapsed = time.perf_counter() - t0
        logger.info("=== DONE:  %s  (%.1fs) ===", name, elapsed)
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error(
            "=== FAILED: %s (%.1fs): %s ===",
            name,
            elapsed,
            exc,
            exc_info=True,
        )
        return False


def main() -> None:
    total_start = time.perf_counter()

    # Import here so failures are caught by _run_step if a module is broken
    from etl.transform.transform_dim_player import transform as dim_player
    from etl.transform.transform_dim_competition import transform as dim_competition
    from etl.transform.transform_fact_match import transform as fact_match
    from etl.transform.transform_fact_player_match import transform as fact_player_match
    from etl.transform.transform_fact_player_club import transform as fact_player_club
    from etl.transform.transform_events import transform as events

    steps = [
        ("dim_player", dim_player),
        ("dim_competition", dim_competition),
        ("fact_match", fact_match),
        ("fact_player_match", fact_player_match),
        ("fact_player_club_season", fact_player_club),
        ("events_statsbomb", events),
    ]

    results = []
    for name, fn in steps:
        success = _run_step(name, fn)
        results.append((name, success))

    total_elapsed = time.perf_counter() - total_start

    # Summary
    logger.info("")
    logger.info("==== TRANSFORM SUMMARY (%.1fs total) ====", total_elapsed)
    failed = []
    for name, success in results:
        status = "OK " if success else "FAIL"
        logger.info("  [%s]  %s", status, name)
        if not success:
            failed.append(name)

    if failed:
        logger.error("Steps with errors: %s", ", ".join(failed))
        sys.exit(1)
    else:
        logger.info("All transform steps completed successfully.")


if __name__ == "__main__":
    main()
