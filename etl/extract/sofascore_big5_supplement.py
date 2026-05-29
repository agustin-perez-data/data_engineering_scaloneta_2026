"""
etl/extract/sofascore_big5_supplement.py
------------------------------------------
Supplementary club stats for Big5 players via Sofascore.

Understat provides goals, assists, xG, xAG, shots and key_passes for Big5
leagues, but NOT tackles, interceptions, pass_pct or GK-specific stats.
This module fetches exactly those missing columns from Sofascore.

Output: data/raw/sofascore_big5_supplement.csv
Columns: player_name, league, tackles, interceptions, blocks, pass_pct,
         saves, save_pct, clean_sheets, goals_against_gk
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.players import SQUAD, BIG5_LEAGUES  # noqa: E402

logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "sofascore_big5_supplement.csv"

# ---------------------------------------------------------------------------
# Tournament + season IDs per Big5 league (Sofascore IDs, season 2024-25)
# ---------------------------------------------------------------------------
BIG5_SOFASCORE_CONFIG: dict[str, dict] = {
    "ENG-Premier League": {"tournament_id": 17,  "season_id": 61627},
    "ESP-La Liga":         {"tournament_id":  8,  "season_id": 61643},
    "ITA-Serie A":         {"tournament_id": 23,  "season_id": 63515},
    "FRA-Ligue 1":         {"tournament_id": 34,  "season_id": 61736},
    "GER-Bundesliga":      {"tournament_id": 35,  "season_id": 63516},
}

# Sofascore player IDs for all Big5 squad players
BIG5_SOFASCORE_PLAYER_IDS: dict[str, int] = {
    # Goalkeepers
    "Emiliano Martínez":    158263,   # Aston Villa
    "Gerónimo Rulli":       128383,   # Olympique Marseille
    "Juan Musso":           263651,   # Atlético Madrid
    # Defenders - ENG
    "Lisandro Martínez":    859999,   # Manchester United
    "Cristian Romero":      829932,   # Tottenham Hotspur
    # Defenders - ESP
    "Nahuel Molina":        831799,   # Atlético Madrid
    # Defenders - FRA
    "Leonardo Balerdi":     928236,   # Olympique Marseille
    "Facundo Medina":       860307,   # Olympique Marseille
    "Nicolás Tagliafico":   158243,   # Olympique Lyonnais
    "Valentín Barco":      1127057,   # RC Strasbourg
    # Midfielders - ENG
    "Enzo Fernández":       974505,   # Chelsea
    "Alexis Mac Allister":  895324,   # Liverpool
    # Midfielders - ESP
    "Giovani Lo Celso":     798835,   # Real Betis
    # Midfielders - GER
    "Exequiel Palacios":    822600,   # Bayer Leverkusen
    # Midfielders - ITA
    "Nicolás Paz":         1171451,   # Como
    # Forwards - ENG  (none currently, Almada/González are ESP)
    # Forwards - ESP
    "Thiago Almada":        944660,   # Atlético Madrid
    "Nicolás González":     901325,   # Atlético Madrid
    "Giuliano Simeone":    1099352,   # Atlético Madrid
    "Julián Álvarez":       944656,   # Atlético Madrid
    # Forwards - ITA
    "Lautaro Martínez":     823984,   # Internazionale
}

# Stats we want FROM Sofascore (those Understat cannot provide for Big5)
SUPPLEMENT_STAT_MAP: dict[str, str] = {
    "tackles":                  "tackles",
    "interceptions":            "interceptions",
    "outfielderBlocks":         "blocks",
    "accuratePassesPercentage": "pass_pct",
    # GK only
    "saves":                    "saves",
    "cleanSheet":               "clean_sheets",
    "goalsConceded":            "goals_against_gk",
    "savePct":                  "save_pct",
}

OUTPUT_COLS = [
    "player_name", "league",
    "tackles", "interceptions", "blocks", "pass_pct",
    "saves", "save_pct", "clean_sheets", "goals_against_gk",
]

_SESSION: Optional[requests.Session] = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })
    return _SESSION


def _get(url: str, pause: float = 1.5) -> Optional[dict]:
    time.sleep(pause)
    try:
        resp = _session().get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("Sofascore GET failed %s — %s", url, exc)
        return None


def _player_stats(player_id: int, tournament_id: int, season_id: int) -> dict[str, float]:
    data = _get(
        f"https://api.sofascore.com/api/v1/player/{player_id}"
        f"/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
    )
    if not data:
        return {}
    raw = data.get("statistics", {})
    result: dict[str, float] = {}
    for ss_key, schema_col in SUPPLEMENT_STAT_MAP.items():
        val = raw.get(ss_key)
        if val is not None:
            try:
                result[schema_col] = float(val)
            except (TypeError, ValueError):
                pass
    return result


def extract_big5_supplement() -> pd.DataFrame:
    """Fetch supplementary stats for all Big5 squad players from Sofascore."""
    rows: list[dict] = []

    for player in SQUAD:
        if player["league"] not in BIG5_LEAGUES:
            continue

        name = player["player_name"]
        league = player["league"]
        config = BIG5_SOFASCORE_CONFIG.get(league)
        player_id = BIG5_SOFASCORE_PLAYER_IDS.get(name)

        if config is None or player_id is None:
            logger.warning("Sofascore Big5: no config/ID for %s (%s)", name, league)
            continue

        stats = _player_stats(player_id, config["tournament_id"], config["season_id"])
        if not stats:
            logger.warning("Sofascore Big5: no stats for %s", name)
            continue

        row: dict = {"player_name": name, "league": league}
        row.update(stats)
        rows.append(row)

        logger.info(
            "  %-25s  tackles=%s  int=%s  pass_pct=%.1f  saves=%s  cs=%s",
            name,
            int(stats.get("tackles", 0)),
            int(stats.get("interceptions", 0)),
            stats.get("pass_pct", 0.0),
            stats.get("saves", "-"),
            stats.get("clean_sheets", "-"),
        )

    df = pd.DataFrame(rows)
    for col in OUTPUT_COLS:
        if col not in df.columns:
            df[col] = None
    return df[OUTPUT_COLS]


def save(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved %d rows to %s", len(df), OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    df = extract_big5_supplement()
    save(df)
    print(df.to_string())
