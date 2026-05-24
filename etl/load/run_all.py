"""
etl/load/run_all.py
---------------------
Main ETL orchestrator.  Applies the DB schema, then loads all tables
in FK-dependency order:

    1. Apply schema (sql/schema.sql)
    2. dim_player + dim_competition  (dimensions)
    3. fact_match
    4. fact_player_match
    5. fact_player_club_season
    6. event_statsbomb

Each step is wrapped in try/except — a failure is logged but subsequent
independent steps still run.  The process exits with code 1 if any step
failed.

Run:
    python -m etl.load.run_all
    # or from project root:
    python etl/load/run_all.py
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
logger = logging.getLogger("run_all")

SCHEMA_SQL = PROJECT_ROOT / "sql" / "schema.sql"


# ---------------------------------------------------------------------------
# Schema application
# ---------------------------------------------------------------------------

def apply_schema() -> None:
    """
    Execute sql/schema.sql against the database.

    We use SQLAlchemy text() execution (split on ';') so we don't require
    psql on the host — the connection details come from the .env file.
    """
    if not SCHEMA_SQL.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_SQL}. "
            "Expected at sql/schema.sql relative to the project root."
        )

    from etl.load.db import get_engine
    from sqlalchemy import text

    schema_text = SCHEMA_SQL.read_text(encoding="utf-8")

    # Split into individual statements (naïve split on ';' is fine for DDL)
    statements = [
        s.strip() for s in schema_text.split(";") if s.strip()
    ]

    engine = get_engine()
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    logger.info("Schema applied from %s (%d statements)", SCHEMA_SQL, len(statements))


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------

def _run_step(name: str, func, *args, **kwargs) -> bool:
    """Execute a callable, log timing and result. Returns True on success."""
    logger.info("=== START: %s ===", name)
    t0 = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        row_info = f" — {result} rows" if isinstance(result, int) else ""
        logger.info("=== DONE:  %s (%.1fs)%s ===", name, elapsed, row_info)
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from etl.load.load_dimensions import load_dim_player, load_dim_competition
    from etl.load.load_fact_match import load as load_fact_match
    from etl.load.load_fact_player_match import load as load_fact_player_match
    from etl.load.load_fact_player_club import load as load_fact_player_club
    from etl.load.load_events import load as load_events

    total_start = time.perf_counter()

    steps = [
        ("apply_schema",          apply_schema),
        ("dim_player",            load_dim_player),
        ("dim_competition",       load_dim_competition),
        ("fact_match",            load_fact_match),
        ("fact_player_match",     load_fact_player_match),
        ("fact_player_club_season", load_fact_player_club),
        ("event_statsbomb",       load_events),
    ]

    results: list[tuple[str, bool]] = []
    for name, fn in steps:
        ok = _run_step(name, fn)
        results.append((name, ok))

        # Schema must succeed before any load step
        if name == "apply_schema" and not ok:
            logger.critical("Schema application failed — aborting load pipeline.")
            sys.exit(1)

    total_elapsed = time.perf_counter() - total_start

    # Summary
    logger.info("")
    logger.info("==== LOAD SUMMARY (%.1fs total) ====", total_elapsed)
    failed = []
    for name, success in results:
        status = "OK  " if success else "FAIL"
        logger.info("  [%s]  %s", status, name)
        if not success:
            failed.append(name)

    if failed:
        logger.error("Steps with errors: %s", ", ".join(failed))
        sys.exit(1)
    else:
        logger.info("All load steps completed successfully.")


if __name__ == "__main__":
    main()
