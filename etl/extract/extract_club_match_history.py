"""
etl/extract/extract_club_match_history.py
-------------------------------------------
Fetches per-match club stats for each squad player (last N matches).

Source: Understat via soccerdata — covers Big5 leagues only.
Non-Big5 players (ARG, MLS, BRA, POR) have no available free source.

Columns per match:
  player_name, league, club, season,
  date, opponent, is_home, result,
  minutes, goals, shots, xg, xag (xa),
  assists, key_passes, yellow_cards, red_cards
  [no shots_on_target, passes, tackles — Understat doesn't provide these]

Output: data/raw/club_match_history.csv
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import flatten_soccerdata, normalize_name
from config.players import SQUAD, BIG5_LEAGUES, LEAGUE_SEASON

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR  = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "club_match_history.csv"

N_MATCHES = 30

NON_BIG5 = [p for p in SQUAD if p["league"] not in BIG5_LEAGUES]

# Understat player IDs (from read_player_season_stats — used as fallback when
# read_player_match_stats fails due to 404 on some match endpoints)
# Confirmed Understat player IDs (from read_player_season_stats queries).
# Used as fallback when read_player_match_stats() returns 404 on some match IDs.
# Players not listed here have no Understat data available.
UNDERSTAT_PLAYER_IDS: dict[str, int] = {
    # ESP-La Liga (confirmed)
    "Juan Musso":        7095,
    "Nahuel Molina":     8963,
    "Giovani Lo Celso":  5681,
    "Julián Álvarez":    10846,
    "Giuliano Simeone":  9796,
    # Note: Nicolás González and Thiago Almada not in Understat 2024-25 (late arrivals)
    # FRA-Ligue 1 (confirmed)
    "Gerónimo Rulli":    2225,
    "Leonardo Balerdi":  7486,
    "Nicolás Tagliafico": 10701,
    "Facundo Medina":    8664,
    "Valentín Barco":    12498,
    # GER-Bundesliga (confirmed)
    "Exequiel Palacios": 8325,
    # ITA-Serie A (confirmed; Nicolás Paz not in Understat — ESPN fallback player)
    "Lautaro Martínez":  7006,
}

FINAL_COLS = [
    "player_name", "league", "club", "season",
    "date", "opponent", "is_home", "result",
    "minutes", "goals", "shots", "xg", "xag",
    "assists", "key_passes", "yellow_cards", "red_cards",
]


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _scrape_player_direct(
    player_name: str, player_id: int, league: str, club: str, season: str
) -> pd.DataFrame | None:
    """
    Fetch per-match history directly from understat.com/player/{id}.
    Used as fallback when read_player_match_stats() returns 404.
    """
    import codecs
    import json
    import re
    import time as _time

    try:
        import cloudscraper
    except ImportError:
        logger.error("cloudscraper not installed")
        return None

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    scraper.headers.update({"Accept-Language": "en-US,en;q=0.9"})

    url = f"https://understat.com/player/{player_id}"
    _time.sleep(4.0)
    try:
        resp = scraper.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("  Direct fetch failed for %s (id=%d): %s", player_name, player_id, exc)
        return None

    # Extract embedded datesData JSON from the HTML
    match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)", resp.text, re.DOTALL)
    if not match:
        logger.warning("  datesData not found in page for %s (id=%d)", player_name, player_id)
        return None

    raw = match.group(1)
    try:
        decoded = codecs.decode(raw, "unicode_escape")
        data = json.loads(decoded)
    except Exception as exc:
        logger.warning("  JSON parse failed for %s: %s", player_name, exc)
        return None

    rows = []
    for m in data:
        is_home = str(m.get("h_a", "h")).lower() == "h"
        opponent = m.get("a_team") if is_home else m.get("h_team")
        # result like "h 2:1" or "a 0:1"
        result_raw = m.get("result", "")
        rows.append({
            "player_name":  player_name,
            "league":       league,
            "club":         club,
            "season":       season,
            "date":         str(m.get("date", ""))[:10],
            "opponent":     opponent,
            "is_home":      is_home,
            "result":       result_raw,
            "minutes":      int(m.get("time", 0) or 0),
            "goals":        int(m.get("goals", 0) or 0),
            "shots":        int(m.get("shots", 0) or 0),
            "xg":           float(m.get("xg", 0) or 0),
            "xag":          float(m.get("xa", 0) or 0),
            "assists":      int(m.get("assists", 0) or 0),
            "key_passes":   int(m.get("key_passes", 0) or 0),
            "yellow_cards": int(m.get("yellow_card", 0) or 0),
            "red_cards":    int(m.get("red_card", 0) or 0),
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = df.sort_values("date").tail(N_MATCHES).reset_index(drop=True)
    logger.info("  Direct: %s — %d matches", player_name, len(df))
    return df


def _parse_game_col(game_val: str) -> tuple[str | None, str | None, bool | None]:
    """
    Try to extract (date, opponent, is_home) from Understat 'game' index values.
    Format examples: '2024-10-15 Arsenal vs Liverpool'
                     'ManUnited 3-0 Arsenal (2024-10-15)'
    Falls back to (None, None, None) if unparseable.
    """
    if not isinstance(game_val, str):
        return None, None, None

    date = None
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", game_val)
    if date_m:
        date = date_m.group(1)

    opponent = None
    is_home  = None
    return date, opponent, is_home


def _scrape_league(league: str, season: str, squad_players: list[dict]) -> pd.DataFrame | None:
    try:
        import soccerdata as sd
    except ImportError:
        logger.error("soccerdata not installed")
        return None

    squad_norm = {normalize_name(p["player_name"]): p for p in squad_players}
    logger.info("Understat per-match: %s %s (%d players)…", league, season, len(squad_players))

    try:
        src = sd.Understat(leagues=league, seasons=season)
        df  = src.read_player_match_stats()
    except Exception as exc:
        logger.warning("read_player_match_stats failed for %s (%s) — trying direct fallback", league, exc)
        # Fallback: scrape each player's page directly
        direct_frames = []
        for p in squad_players:
            pid = UNDERSTAT_PLAYER_IDS.get(p["player_name"])
            if pid is None:
                logger.info("  No Understat ID for %s — skipping", p["player_name"])
                continue
            pdf = _scrape_player_direct(
                p["player_name"], pid, league, p["club"], season
            )
            if pdf is not None:
                direct_frames.append(pdf)
        if direct_frames:
            result = pd.concat(direct_frames, ignore_index=True)
            logger.info("%s (direct): %d rows (%d players)", league, len(result), result["player_name"].nunique())
            return result
        return None

    df = flatten_soccerdata(df)
    logger.info("  raw per-match shape: %s | cols: %s", df.shape, list(df.columns[:15]))

    player_col = _find_col(df, "player", "player_name", "name")
    if not player_col:
        logger.warning("  Cannot find player column for %s", league)
        return None

    df["_norm"] = df[player_col].apply(lambda n: normalize_name(str(n)))
    df = df[df["_norm"].isin(squad_norm)].copy()

    if df.empty:
        logger.info("  No squad players found in per-match data for %s", league)
        return None

    df["player_name"] = df["_norm"].map(lambda n: squad_norm[n]["player_name"])
    df["league"]      = league
    df["club"]        = df["_norm"].map(lambda n: squad_norm[n]["club"])
    df["season"]      = season

    # ── parse game identifier for date info ─────────────────────────────
    game_col = _find_col(df, "game", "match", "date")
    if game_col and game_col != "date":
        df[["date", "_opp", "_is_home"]] = df[game_col].apply(
            lambda v: pd.Series(_parse_game_col(str(v)))
        )
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
    else:
        df["date"] = None

    # ── rename stat columns ──────────────────────────────────────────────
    renames = {}
    def _try(*src_cols, out: str) -> None:
        for c in src_cols:
            if c in df.columns and c not in renames:
                renames[c] = out
                break

    _try("minutes", "time", out="minutes")
    _try("goals", "gls", out="goals")
    _try("shots", "sh", out="shots")
    _try("xg", out="xg")
    _try("xa", "xag", out="xag")
    _try("assists", "ast", out="assists")
    _try("key_passes", "kp", out="key_passes")
    _try("yellow_cards", "yellow", "yc", out="yellow_cards")
    _try("red_cards", "red", "rc", out="red_cards")

    df = df.rename(columns=renames)

    # ── home / away / result ─────────────────────────────────────────────
    for col in ("is_home", "h_a", "home_away", "venue"):
        if col in df.columns:
            df["is_home"] = df[col].apply(
                lambda v: True if str(v).lower() in ("h", "home", "1", "true") else False
            )
            break
    else:
        df["is_home"] = None

    for col in ("result", "w_d_l", "res"):
        if col in df.columns:
            df["result"] = df[col]
            break
    else:
        df["result"] = None

    df["opponent"] = df.get("_opp", None)

    # ── per player: sort chronologically and keep last N ─────────────────
    chunks = []
    for pname, grp in df.groupby("player_name"):
        grp = grp.copy()
        if "date" in grp.columns and grp["date"].notna().any():
            grp = grp.sort_values("date")
        else:
            # keep original order (Understat returns chronological by default)
            pass
        chunks.append(grp.tail(N_MATCHES))

    result = pd.concat(chunks, ignore_index=True)

    logger.info(
        "  %s: %d rows (%d players, up to %d matches each)",
        league, len(result), result["player_name"].nunique(), N_MATCHES,
    )
    return result


def extract() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []

    for league in sorted(BIG5_LEAGUES):
        players = [p for p in SQUAD if p["league"] == league]
        if not players:
            continue
        season = LEAGUE_SEASON.get(league, "2024-25")
        df = _scrape_league(league, season, players)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        logger.error("No per-match data collected")
        return pd.DataFrame(columns=FINAL_COLS)

    combined = pd.concat(frames, ignore_index=True)

    for col in FINAL_COLS:
        if col not in combined.columns:
            combined[col] = None

    num_cols = ["minutes", "goals", "shots", "xg", "xag", "assists", "key_passes",
                "yellow_cards", "red_cards"]
    for col in num_cols:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    combined = combined[FINAL_COLS].reset_index(drop=True)

    combined.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info(
        "Saved %d rows (%d players) to %s",
        len(combined), combined["player_name"].nunique(), OUT_FILE,
    )

    # Report non-Big5 players without data
    if NON_BIG5:
        logger.info(
            "No data available (non-Big5): %s",
            [p["player_name"] for p in NON_BIG5],
        )

    return combined


if __name__ == "__main__":
    extract()
