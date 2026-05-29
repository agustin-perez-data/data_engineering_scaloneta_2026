"""
etl/transform/transform_fact_player_match.py
----------------------------------------------
Reads per-match player stats CSVs (outfield + GK) from data/raw/,
merges them, resolves player_id and match_id foreign keys, and
writes data/transformed/fact_player_match.csv.

Input files:
    data/raw/argentina_player_match_stats.csv   — outfield stats
    data/raw/argentina_gk_match_stats.csv       — GK-specific stats

Output columns:
    match_id, player_id, started, minutes_played,
    goals, assists, shots, shots_on_target, xg, xag,
    passes_completed, passes_attempted, pass_pct,
    progressive_passes, key_passes, progressive_carries,
    tackles, interceptions, blocks, yellow_cards, red_cards,
    saves, save_pct, clean_sheet, psxg
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import normalize_name
from etl.transform.player_name_map import FBREF_TO_CANONICAL, resolve_player_name

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"

PLAYER_STATS_CSV = RAW_DIR / "argentina_player_match_stats.csv"
GK_STATS_CSV = RAW_DIR / "argentina_gk_match_stats.csv"
SOFASCORE_NT_CSV = RAW_DIR / "sofascore_nt_match_stats.csv"
DIM_PLAYER_CSV = TRANSFORMED_DIR / "dim_player.csv"
FACT_MATCH_CSV = TRANSFORMED_DIR / "fact_match.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "fact_player_match.csv"

# Counting stats that should be 0 when missing (not left as NaN)
_COUNT_COLS = [
    "goals", "assists", "shots", "shots_on_target",
    "passes_completed", "passes_attempted",
    "progressive_passes", "key_passes", "progressive_carries",
    "tackles", "interceptions", "blocks",
    "yellow_cards", "red_cards",
    "saves",
]

_BOOL_COLS = ["clean_sheet"]

# Float stats that stay NaN when missing
_FLOAT_COLS = ["xg", "xag", "pass_pct", "save_pct", "psxg"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _find_col(candidates: list[str], df: pd.DataFrame) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _resolve_player_id(
    raw_name: str,
    dim_player: pd.DataFrame,
    name_to_id: dict[str, int],
    norm_to_id: dict[str, int],
) -> int | None:
    """Try exact match → canonical map → normalize match → dim_player normalize."""
    if not isinstance(raw_name, str):
        return None

    # 1. Direct match against dim_player.player_name
    if raw_name in name_to_id:
        return name_to_id[raw_name]

    # 2. Via FBREF_TO_CANONICAL map
    canonical = resolve_player_name(raw_name, FBREF_TO_CANONICAL)
    if canonical and canonical in name_to_id:
        return name_to_id[canonical]

    # 3. Normalize-based match against dim_player
    norm = normalize_name(raw_name)
    if norm in norm_to_id:
        return norm_to_id[norm]

    return None


def _build_match_id(date: str, opponent: str) -> str:
    """Re-build match_id in same format as transform_fact_match."""
    import re
    ts = pd.to_datetime(date, errors="coerce")
    if pd.isna(ts):
        return ""
    date_str = ts.strftime("%Y%m%d")
    opp_clean = re.sub(r"\s+", "_", str(opponent).strip())[:10]
    return f"ARG_{date_str}_{opp_clean}"


# ---------------------------------------------------------------------------
# Main transform
# ---------------------------------------------------------------------------

def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Load dimension tables for FK lookups
    # ------------------------------------------------------------------
    dim_player = pd.read_csv(DIM_PLAYER_CSV, encoding="utf-8")
    name_to_id: dict[str, int] = dict(
        zip(dim_player["player_name"], dim_player["player_id"])
    )
    norm_to_id: dict[str, int] = {
        normalize_name(n): pid for n, pid in name_to_id.items()
    }

    fact_match = pd.read_csv(FACT_MATCH_CSV, encoding="utf-8")
    # Build lookup: (YYYYMMDD_date, opponent_normalised) → match_id
    fact_match["_date_norm"] = pd.to_datetime(
        fact_match["date"], errors="coerce"
    ).dt.strftime("%Y%m%d")
    fact_match["_opp_norm"] = fact_match["opponent"].str.strip().str.lower()
    match_lookup: dict[tuple[str, str], str] = {
        (r["_date_norm"], r["_opp_norm"]): r["match_id"]
        for _, r in fact_match.iterrows()
    }

    # ------------------------------------------------------------------
    # Load outfield player stats (StatsBomb — WC2022 + CA2024)
    # ------------------------------------------------------------------
    if not PLAYER_STATS_CSV.exists():
        logger.error("Missing %s — run extract step first", PLAYER_STATS_CSV)
        return pd.DataFrame()

    df = pd.read_csv(PLAYER_STATS_CSV, encoding="utf-8")
    df = _normalise_cols(df)

    # ------------------------------------------------------------------
    # Merge StatsBomb GK stats if available
    # ------------------------------------------------------------------
    if GK_STATS_CSV.exists():
        gk = pd.read_csv(GK_STATS_CSV, encoding="utf-8")
        gk = _normalise_cols(gk)

        # Identify join keys in GK frame
        gk_player_col = _find_col(["player", "player_name", "name"], gk)
        gk_date_col = _find_col(["date"], gk)
        if gk_player_col and gk_date_col:
            gk_cols_to_merge = [gk_player_col, gk_date_col]
            for col in ["saves", "save_pct", "clean_sheet", "psxg", "cs"]:
                if col in gk.columns:
                    gk_cols_to_merge.append(col)

            gk_sub = gk[gk_cols_to_merge].copy()
            # Rename cs → clean_sheet if needed
            if "cs" in gk_sub.columns and "clean_sheet" not in gk_sub.columns:
                gk_sub = gk_sub.rename(columns={"cs": "clean_sheet"})

            player_col = _find_col(["player", "player_name", "name"], df)
            date_col = _find_col(["date"], df)

            if player_col and date_col:
                df = df.merge(
                    gk_sub.rename(
                        columns={gk_player_col: player_col, gk_date_col: date_col}
                    ),
                    on=[player_col, date_col],
                    how="left",
                    suffixes=("", "_gk"),
                )
                # Prefer GK columns over any existing ones
                for col in ["saves", "save_pct", "clean_sheet", "psxg"]:
                    gk_col = f"{col}_gk"
                    if gk_col in df.columns:
                        df[col] = df[col].combine_first(df[gk_col])
                        df.drop(columns=[gk_col], inplace=True)
    else:
        logger.warning("GK stats file not found: %s", GK_STATS_CSV)

    # ------------------------------------------------------------------
    # Append Sofascore NT match stats (CA2021 + WCQ 2022/2026)
    # GK saves/goals_against/clean_sheet are already inline for GKs.
    # ------------------------------------------------------------------
    if SOFASCORE_NT_CSV.exists():
        df_sc = pd.read_csv(SOFASCORE_NT_CSV, encoding="utf-8")
        df_sc = _normalise_cols(df_sc)
        df = pd.concat([df, df_sc], ignore_index=True)
        logger.info(
            "Appended Sofascore NT stats: %d rows (total now %d)",
            len(df_sc), len(df),
        )
    else:
        logger.warning("Sofascore NT stats not found: %s", SOFASCORE_NT_CSV)

    # ------------------------------------------------------------------
    # Identify source columns
    # ------------------------------------------------------------------
    player_col = _find_col(["player", "player_name", "name"], df)
    date_col = _find_col(["date"], df)
    opp_col = _find_col(["opponent", "opp"], df)
    started_col = _find_col(["started", "start"], df)
    minutes_col = _find_col(["min", "minutes", "minutes_played"], df)

    for label, col in [("player", player_col), ("date", date_col), ("opponent", opp_col)]:
        if col is None:
            raise ValueError(
                f"Required column '{label}' not found in {PLAYER_STATS_CSV}. "
                f"Available: {list(df.columns)}"
            )

    # Column aliases from FBRef multi-level headers
    col_map = {
        # stat name → list of possible column names in df
        "goals": ["gls", "goals", "g"],
        "assists": ["ast", "assists", "a"],
        "shots": ["sh", "shots"],
        "shots_on_target": ["sot", "shots_on_target"],
        "xg": ["xg", "expected_xg"],
        "xag": ["xag", "expected_xag"],
        "passes_completed": ["cmp", "passes_cmp", "passes_completed"],
        "passes_attempted": ["att", "passes_att", "passes_attempted"],
        "pass_pct": ["cmp%", "passes_cmp%", "pass_pct", "pass_%"],
        "progressive_passes": ["prg", "prgp", "progressive_passes"],
        "key_passes": ["kp", "key_passes"],
        "progressive_carries": ["prgc", "progressive_carries"],
        "tackles": ["tkl", "tackles"],
        "interceptions": ["int", "interceptions"],
        "blocks": ["blocks", "blk"],
        "yellow_cards": ["crdy", "yellow_cards", "yc"],
        "red_cards": ["crdr", "red_cards", "rc"],
        "saves": ["saves", "sav"],
        "save_pct": ["save%", "save_pct"],
        "clean_sheet": ["cs", "clean_sheet"],
        "psxg": ["psxg", "post_shot_xg"],
    }

    def _get_col(stat: str) -> str | None:
        return _find_col(col_map.get(stat, [stat]), df)

    # ------------------------------------------------------------------
    # Build output rows
    # ------------------------------------------------------------------
    rows = []
    unresolved_players: set[str] = set()
    unresolved_matches: set[str] = set()

    for _, row in df.iterrows():
        raw_name = str(row[player_col]).strip() if pd.notna(row[player_col]) else ""
        raw_date = str(row[date_col]).strip() if pd.notna(row[date_col]) else ""
        raw_opp = str(row[opp_col]).strip() if pd.notna(row[opp_col]) else ""

        # --- player FK ---
        player_id = _resolve_player_id(raw_name, dim_player, name_to_id, norm_to_id)
        if player_id is None:
            unresolved_players.add(raw_name)
            continue  # skip players not in our 55-man squad

        # --- match FK ---
        date_norm = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(date_norm):
            logger.debug("Skipping row with unparseable date: %r", raw_date)
            continue
        date_str = date_norm.strftime("%Y%m%d")
        opp_norm = raw_opp.lower()
        match_id = match_lookup.get((date_str, opp_norm))
        if match_id is None:
            # Try ±1 day (Sofascore vs FBRef timezone offset)
            for delta in (-1, 1):
                shifted = (date_norm + pd.Timedelta(days=delta)).strftime("%Y%m%d")
                match_id = match_lookup.get((shifted, opp_norm))
                if match_id:
                    break
        if match_id is None:
            # Try partial opponent name match on same date
            for (d, o), mid in match_lookup.items():
                if d == date_str and (o in opp_norm or opp_norm in o):
                    match_id = mid
                    break
        if match_id is None:
            unresolved_matches.add(f"{raw_date} vs {raw_opp}")
            continue

        # --- started ---
        started: bool | None = None
        if started_col and pd.notna(row.get(started_col)):
            sv = str(row[started_col]).strip().upper()
            started = sv == "Y"

        # --- minutes ---
        minutes_played: int | None = None
        if minutes_col:
            m = pd.to_numeric(row.get(minutes_col), errors="coerce")
            minutes_played = int(m) if pd.notna(m) else None

        # --- build stat dict ---
        stat_row: dict = {
            "match_id": match_id,
            "player_id": player_id,
            "started": started,
            "minutes_played": minutes_played,
        }

        for stat in _COUNT_COLS:
            src_col = _get_col(stat)
            if src_col:
                val = pd.to_numeric(row.get(src_col), errors="coerce")
                stat_row[stat] = int(val) if pd.notna(val) else 0
            else:
                stat_row[stat] = 0

        for stat in _FLOAT_COLS:
            src_col = _get_col(stat)
            if src_col:
                val = pd.to_numeric(row.get(src_col), errors="coerce")
                stat_row[stat] = float(val) if pd.notna(val) else None
            else:
                stat_row[stat] = None

        for stat in _BOOL_COLS:
            src_col = _get_col(stat)
            if src_col:
                raw_val = row.get(src_col)
                if pd.isna(raw_val) if isinstance(raw_val, float) else raw_val is None:
                    stat_row[stat] = False
                else:
                    stat_row[stat] = bool(raw_val)
            else:
                stat_row[stat] = False

        rows.append(stat_row)

    if unresolved_players:
        logger.info(
            "Skipped %d player name(s) not in squad: %s",
            len(unresolved_players),
            sorted(unresolved_players),
        )
    if unresolved_matches:
        logger.warning(
            "Could not resolve match_id for %d row(s): %s",
            len(unresolved_matches),
            sorted(unresolved_matches),
        )

    df_out = pd.DataFrame(rows)

    # Ensure all expected output columns exist
    all_output_cols = (
        ["match_id", "player_id", "started", "minutes_played"]
        + _COUNT_COLS
        + _FLOAT_COLS
    )
    for col in all_output_cols:
        if col not in df_out.columns:
            df_out[col] = None

    df_out = df_out[all_output_cols]

    df_out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("fact_player_match: %d rows → %s", len(df_out), OUTPUT_PATH)
    return df_out


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
