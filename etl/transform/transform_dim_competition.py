"""
etl/transform/transform_dim_competition.py
-------------------------------------------
Reads data/raw/argentina_matches.csv, extracts the unique competitions
Argentina played in, and writes data/transformed/dim_competition.csv.

Output columns:
    competition_id, name, short_name, type, year, confederation
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.transform.player_name_map import COMPETITION_MAP

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"

MATCHES_CSV = RAW_DIR / "argentina_matches.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "dim_competition.csv"

# Short names for display / Metabase labels
_SHORT_NAMES: dict[str, str] = {
    "WC": "World Cup",
    "CA": "Copa América",
    "WCQ": "WC Qualifying",
    "FRIENDLY": "Friendly",
}

# CONMEBOL competitions
_CONMEBOL_TYPES = {"CA", "WCQ"}
_FIFA_TYPES = {"WC"}


def _infer_year(comp_name: str, comp_type: str, dates: pd.Series) -> int | None:
    """Infer the 4-digit year for a competition from the majority of its match dates."""
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return None

    parsed = pd.to_datetime(valid_dates, errors="coerce").dropna()
    if parsed.empty:
        return None

    years = parsed.dt.year
    return int(years.mode().iloc[0])


def transform() -> pd.DataFrame:
    """Build dim_competition from argentina_matches.csv."""

    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    matches = pd.read_csv(MATCHES_CSV, encoding="utf-8")

    # Normalise column names
    matches.columns = [c.strip().lower().replace(" ", "_") for c in matches.columns]

    # Identify the competition and date columns (handle FBRef column naming variants)
    comp_col = next(
        (c for c in matches.columns if "comp" in c or "competition" in c), None
    )
    date_col = next((c for c in matches.columns if c == "date"), None)

    if comp_col is None:
        raise ValueError(
            f"Cannot find competition column in {MATCHES_CSV}. "
            f"Available columns: {list(matches.columns)}"
        )

    rows = []
    comp_id = 1

    for comp_name in sorted(matches[comp_col].dropna().unique()):
        comp_name_str = str(comp_name).strip()

        # Lookup type from map
        mapped = COMPETITION_MAP.get(comp_name_str)
        if mapped is None:
            # Try a case-insensitive search
            lower_key = comp_name_str.lower()
            for k, v in COMPETITION_MAP.items():
                if k.lower() == lower_key:
                    mapped = v
                    break

        if mapped is None:
            logger.warning("Unknown competition %r — skipping", comp_name_str)
            continue

        comp_type, fixed_year = mapped

        if fixed_year is not None:
            year = fixed_year
        else:
            comp_dates = (
                matches.loc[matches[comp_col] == comp_name, date_col]
                if date_col
                else pd.Series([], dtype=object)
            )
            year = _infer_year(comp_name_str, comp_type, comp_dates)

        confederation = (
            "CONMEBOL"
            if comp_type in _CONMEBOL_TYPES
            else ("FIFA" if comp_type in _FIFA_TYPES else "FIFA/UEFA")
        )

        rows.append(
            {
                "competition_id": comp_id,
                "name": comp_name_str,
                "short_name": _SHORT_NAMES.get(comp_type, comp_type),
                "type": comp_type,
                "year": year,
                "confederation": confederation,
            }
        )
        comp_id += 1

    df = pd.DataFrame(rows)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("dim_competition: %d rows → %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
