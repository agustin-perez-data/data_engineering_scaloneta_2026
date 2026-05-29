"""
etl/transform/transform_events.py
------------------------------------
Reads data/raw/argentina_events.csv (StatsBomb format) and maps
player names + match IDs to our schema, then writes
data/transformed/events_statsbomb.csv.

StatsBomb match IDs are resolved via data/raw/argentina_statsbomb_matches.csv
(a lookup table of statsbomb_match_id → date + opponent).

Rows where player_id is NULL (players outside the 55-man squad) are dropped.

Output columns:
    event_id, match_id, player_id, period, minute, second,
    event_type, event_subtype,
    x, y, end_x, end_y,
    outcome, under_pressure, counterpress
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
from etl.transform.player_name_map import STATSBOMB_TO_CANONICAL, resolve_player_name

logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRANSFORMED_DIR = PROJECT_ROOT / "data" / "transformed"

EVENTS_CSV = RAW_DIR / "statsbomb" / "argentina_events.csv"
SB_MATCHES_CSV = RAW_DIR / "statsbomb" / "argentina_statsbomb_matches.csv"
DIM_PLAYER_CSV = TRANSFORMED_DIR / "dim_player.csv"
FACT_MATCH_CSV = TRANSFORMED_DIR / "fact_match.csv"
OUTPUT_PATH = TRANSFORMED_DIR / "events_statsbomb.csv"


def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _find_col(candidates: list[str], df: pd.DataFrame) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def transform() -> pd.DataFrame:
    TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

    if not EVENTS_CSV.exists():
        logger.error("Missing %s — run extract step first", EVENTS_CSV)
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Load dim_player
    # ------------------------------------------------------------------
    dim_player = pd.read_csv(DIM_PLAYER_CSV, encoding="utf-8")
    name_to_id: dict[str, int] = dict(
        zip(dim_player["player_name"], dim_player["player_id"])
    )
    norm_to_id: dict[str, int] = {
        normalize_name(n): pid for n, pid in name_to_id.items()
    }

    # ------------------------------------------------------------------
    # Build statsbomb_match_id → fact_match match_id lookup
    # ------------------------------------------------------------------
    fact_match = pd.read_csv(FACT_MATCH_CSV, encoding="utf-8")
    fact_match["_date_norm"] = pd.to_datetime(
        fact_match["date"], errors="coerce"
    ).dt.strftime("%Y%m%d")
    fact_match["_opp_norm"] = fact_match["opponent"].str.strip().str.lower()

    # fact_match keyed by (date_YYYYMMDD, opp_lower)
    fm_lookup: dict[tuple[str, str], str] = {
        (r["_date_norm"], r["_opp_norm"]): r["match_id"]
        for _, r in fact_match.iterrows()
    }

    # StatsBomb match_id → our match_id
    sb_match_id_map: dict[str | int, str] = {}

    if SB_MATCHES_CSV.exists():
        sb_matches = pd.read_csv(SB_MATCHES_CSV, encoding="utf-8")
        sb_matches = _normalise_cols(sb_matches)

        sb_id_col = _find_col(["match_id", "statsbomb_match_id", "id"], sb_matches)
        sb_date_col = _find_col(["date", "match_date"], sb_matches)
        sb_opp_col = _find_col(["opponent", "away_team", "opp"], sb_matches)

        if sb_id_col and sb_date_col and sb_opp_col:
            for _, r in sb_matches.iterrows():
                sb_id = r[sb_id_col]
                date_norm = pd.to_datetime(r[sb_date_col], errors="coerce")
                if pd.isna(date_norm):
                    continue
                date_str = date_norm.strftime("%Y%m%d")
                opp_str = str(r[sb_opp_col]).strip().lower()

                fact_mid = fm_lookup.get((date_str, opp_str))
                if fact_mid is None:
                    for (d, o), mid in fm_lookup.items():
                        if d == date_str and (o in opp_str or opp_str in o):
                            fact_mid = mid
                            break
                if fact_mid:
                    sb_match_id_map[sb_id] = fact_mid
        else:
            logger.warning(
                "StatsBomb matches CSV missing expected columns. "
                "Available: %s", list(sb_matches.columns)
            )
    else:
        logger.warning(
            "StatsBomb matches file not found: %s. "
            "match_id resolution will fall back to date+opponent columns.", SB_MATCHES_CSV
        )

    # ------------------------------------------------------------------
    # Load events
    # ------------------------------------------------------------------
    events = pd.read_csv(EVENTS_CSV, encoding="utf-8")
    events = _normalise_cols(events)

    player_col = _find_col(["player", "player_name", "player_id"], events)
    direct_match_col = _find_col(["match_fbref_id"], events)
    sb_match_col = _find_col(["match_id", "statsbomb_match_id"], events)
    period_col = _find_col(["period"], events)
    minute_col = _find_col(["minute"], events)
    second_col = _find_col(["second"], events)
    type_col = _find_col(["type", "event_type", "type_name"], events)
    subtype_col = _find_col(["sub_type", "event_subtype", "subtype", "type_subtype"], events)
    x_col = _find_col(["x", "location_x", "start_x"], events)
    y_col = _find_col(["y", "location_y", "start_y"], events)
    end_x_col = _find_col(["end_x", "end_location_x"], events)
    end_y_col = _find_col(["end_y", "end_location_y"], events)
    outcome_col = _find_col(["outcome", "outcome_name"], events)
    pressure_col = _find_col(["under_pressure"], events)
    counterpress_col = _find_col(["counterpress"], events)

    # ------------------------------------------------------------------
    # Resolve player_id for every event row
    # ------------------------------------------------------------------
    def _resolve_pid(raw: object) -> int | None:
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            return None
        raw_str = str(raw).strip()
        if raw_str in name_to_id:
            return name_to_id[raw_str]
        canonical = resolve_player_name(raw_str, STATSBOMB_TO_CANONICAL)
        if canonical and canonical in name_to_id:
            return name_to_id[canonical]
        norm = normalize_name(raw_str)
        return norm_to_id.get(norm)

    if player_col:
        events["_player_id"] = events[player_col].apply(_resolve_pid)
    else:
        logger.error("Cannot find player column in events CSV")
        return pd.DataFrame()

    # Drop events for players outside our squad
    before = len(events)
    events = events[events["_player_id"].notna()].copy()
    dropped = before - len(events)
    if dropped:
        logger.info("Dropped %d events for players not in squad", dropped)

    events["_player_id"] = events["_player_id"].astype(int)

    # ------------------------------------------------------------------
    # Resolve match_id — prefer direct match_fbref_id column if available
    # ------------------------------------------------------------------
    if direct_match_col:
        events["_match_id"] = events[direct_match_col].where(events[direct_match_col].notna(), None)
        logger.info("Using direct match_fbref_id column for match_id resolution")
    else:
        def _resolve_match_id(sb_id: object) -> str | None:
            if sb_id is None or (isinstance(sb_id, float) and np.isnan(sb_id)):
                return None
            return sb_match_id_map.get(sb_id) or sb_match_id_map.get(str(sb_id))

        if sb_match_col:
            events["_match_id"] = events[sb_match_col].apply(_resolve_match_id)
        else:
            events["_match_id"] = None
            logger.warning("No match_id column found in events CSV")

    unresolved = events["_match_id"].isna().sum()
    if unresolved:
        logger.warning(
            "%d events have no resolved match_id — they will have NULL match_id", unresolved
        )

    # ------------------------------------------------------------------
    # Build output DataFrame
    # ------------------------------------------------------------------
    def _float_col(col: str | None) -> pd.Series:
        if col and col in events.columns:
            return pd.to_numeric(events[col], errors="coerce")
        return pd.Series([None] * len(events), dtype=float)

    def _str_col(col: str | None) -> pd.Series:
        if col and col in events.columns:
            return events[col].astype(str).replace("nan", None)
        return pd.Series([None] * len(events), dtype=object)

    def _bool_col(col: str | None) -> pd.Series:
        if col and col in events.columns:
            return events[col].map(
                lambda v: True if str(v).strip().lower() in ("true", "1", "yes") else
                          (False if str(v).strip().lower() in ("false", "0", "no") else None)
            )
        return pd.Series([None] * len(events), dtype=object)

    import uuid as _uuid
    df_out = pd.DataFrame(
        {
            "event_id": [str(_uuid.uuid4()) for _ in range(len(events))],
            "match_id": events["_match_id"].values,
            "player_id": events["_player_id"].values,
            "period": pd.to_numeric(events[period_col], errors="coerce").values
            if period_col else None,
            "minute": pd.to_numeric(events[minute_col], errors="coerce").values
            if minute_col else None,
            "second": pd.to_numeric(events[second_col], errors="coerce").values
            if second_col else None,
            "event_type": _str_col(type_col).values,
            "event_subtype": _str_col(subtype_col).values,
            "x": _float_col(x_col).values,
            "y": _float_col(y_col).values,
            "end_x": _float_col(end_x_col).values,
            "end_y": _float_col(end_y_col).values,
            "outcome": _str_col(outcome_col).values,
            "xg": _float_col("xg" if "xg" in events.columns else None).values,
            "under_pressure": _bool_col(pressure_col).values,
            "counterpress": _bool_col(counterpress_col).values,
        }
    )

    df_out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("events_statsbomb: %d rows → %s", len(df_out), OUTPUT_PATH)
    return df_out


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    transform()
