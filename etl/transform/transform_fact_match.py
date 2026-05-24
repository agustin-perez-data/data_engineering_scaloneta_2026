"""
etl/transform/transform_fact_match.py
---------------------------------------
Reads data/raw/argentina_matches.csv + data/transformed/dim_competition.csv
and produces data/transformed/fact_match.csv with one row per match.

match_id format: "ARG_" + YYYYMMDD + "_" + opponent_name[:10]
  e.g. "ARG_20221018_Ecuador"

Output columns:
    match_id, date, competition_id, opponent, is_home,
    goals_for, goals_against, result, xg_for, xg_against
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.transform.player_name_map import COMPETITION_MAP

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"

MATCHES_CSV = RAW_DIR / "argentina_matches.csv"
DIM_COMP_CSV = TRANSFORMED_DIR / "dim_competition.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "fact_match.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_match_id(date: pd.Timestamp, opponent: str) -> str:
    """ARG_YYYYMMDD_OpponentNa (opponent truncated to 10 chars, spaces removed)."""
    date_str = date.strftime("%Y%m%d")
    opp_clean = re.sub(r"\s+", "_", opponent.strip())[:10]
    return f"ARG_{date_str}_{opp_clean}"


def _parse_xg(val: object) -> float | None:
    """Convert an xG cell ('0.72', '-', NaN, None) to float or None."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if s in ("", "-", "N/A", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _determine_result(gf: int, ga: int) -> str:
    """W / D / L from Argentina's perspective."""
    if gf > ga:
        return "W"
    if gf == ga:
        return "D"
    return "L"


def transform() -> pd.DataFrame:
    """Build fact_match from raw matches CSV."""

    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Load raw matches
    # ------------------------------------------------------------------
    matches = pd.read_csv(MATCHES_CSV, encoding="utf-8")
    matches.columns = [c.strip().lower().replace(" ", "_") for c in matches.columns]

    # ------------------------------------------------------------------
    # Load dim_competition for FK lookup
    # ------------------------------------------------------------------
    dim_comp = pd.read_csv(DIM_COMP_CSV, encoding="utf-8")
    # Support both "name" (old) and "competition_name" (new) column naming
    _comp_name_col = "competition_name" if "competition_name" in dim_comp.columns else "name"
    comp_lookup: dict[str, int] = dict(
        zip(dim_comp[_comp_name_col].str.strip(), dim_comp["competition_id"])
    )

    # ------------------------------------------------------------------
    # Identify columns — FBRef exports use varying names
    # ------------------------------------------------------------------
    def _find_col(candidates: list[str], df: pd.DataFrame) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        return None

    date_col = _find_col(["date"], matches)
    comp_col = _find_col(["comp", "competition"], matches)
    venue_col = _find_col(["venue"], matches)
    opp_col = _find_col(["opponent", "opp"], matches)
    gf_col = _find_col(["gf", "goals_for", "g_f"], matches)
    ga_col = _find_col(["ga", "goals_against", "g_a"], matches)
    xg_col = _find_col(["xg", "xg_for", "xgf"], matches)
    xga_col = _find_col(["xga", "xg_against", "xgforsq", "xg_a"], matches)

    for col_name, col_val in [
        ("date", date_col),
        ("competition", comp_col),
        ("opponent", opp_col),
        ("goals_for", gf_col),
        ("goals_against", ga_col),
    ]:
        if col_val is None:
            raise ValueError(
                f"Required column '{col_name}' not found in {MATCHES_CSV}. "
                f"Available: {list(matches.columns)}"
            )

    # ------------------------------------------------------------------
    # Parse and filter
    # ------------------------------------------------------------------
    matches[date_col] = pd.to_datetime(matches[date_col], errors="coerce")

    # Drop rows without a date or score (unplayed / future matches)
    matches = matches.dropna(subset=[date_col, gf_col, ga_col]).copy()

    # Coerce goals to int
    matches[gf_col] = pd.to_numeric(matches[gf_col], errors="coerce")
    matches[ga_col] = pd.to_numeric(matches[ga_col], errors="coerce")
    matches = matches.dropna(subset=[gf_col, ga_col]).copy()
    matches[gf_col] = matches[gf_col].astype(int)
    matches[ga_col] = matches[ga_col].astype(int)

    # ------------------------------------------------------------------
    # Build output rows
    # ------------------------------------------------------------------
    rows = []
    for _, row in matches.iterrows():
        date = row[date_col]
        opponent = str(row[opp_col]).strip()
        comp_name = str(row[comp_col]).strip() if comp_col else ""

        match_id = _build_match_id(date, opponent)

        # is_home: FBRef venue column contains "Home" or "H"
        if venue_col and pd.notna(row[venue_col]):
            venue_str = str(row[venue_col]).strip().lower()
            is_home = venue_str in ("home", "h") or venue_str.startswith("home")
        else:
            is_home = None

        gf = int(row[gf_col])
        ga = int(row[ga_col])
        result = _determine_result(gf, ga)

        # Competition FK
        comp_id = comp_lookup.get(comp_name)
        if comp_id is None:
            # Case-insensitive fallback
            for k, v in comp_lookup.items():
                if k.lower() == comp_name.lower():
                    comp_id = v
                    break
        if comp_id is None:
            logger.warning("match %s: competition %r not in dim_competition", match_id, comp_name)

        # xG
        xg_for = _parse_xg(row[xg_col]) if xg_col else None
        xg_against = _parse_xg(row[xga_col]) if xga_col else None

        # is_neutral
        neutral_col = next((c for c in matches.columns if c == "is_neutral"), None)
        if neutral_col and pd.notna(row.get(neutral_col)):
            is_neutral = bool(row[neutral_col])
        else:
            is_neutral = None

        rows.append(
            {
                "match_id": match_id,
                "date": date.date().isoformat(),
                "competition_id": comp_id,
                "opponent": opponent,
                "is_home": is_home,
                "is_neutral": is_neutral,
                "goals_for": gf,
                "goals_against": ga,
                "result": result,
                "xg_for": xg_for,
                "xg_against": xg_against,
            }
        )

    df = pd.DataFrame(rows)

    # Deduplicate on match_id (keep first occurrence)
    dupes = df.duplicated(subset=["match_id"], keep="first")
    if dupes.any():
        logger.warning(
            "Dropping %d duplicate match_id rows: %s",
            dupes.sum(),
            df.loc[dupes, "match_id"].tolist(),
        )
    df = df[~dupes].reset_index(drop=True)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("fact_match: %d rows → %s", len(df), OUTPUT_PATH)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
