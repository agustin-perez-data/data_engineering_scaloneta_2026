"""
Squad configuration for Argentina national team — 2026 World Cup cycle.
26-player squad covering all positions and clubs.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

# ---------------------------------------------------------------------------
# Full squad  (3 GK + 9 DF + 7 MF + 7 FW = 26)
# Keys
#   player_name    : full name with accents
#   short_name     : nickname / abbreviated name used in displays
#   position       : GK | DF | MF | FW
#   club           : current club (long-form)
#   league         : soccerdata / FBRef league code
#   statsbomb_name : name as it appears in StatsBomb open-data
# ---------------------------------------------------------------------------
SQUAD: List[Dict[str, str]] = [
    # ── GOALKEEPERS (3) ─────────────────────────────────────────────────────
    {
        "player_name": "Emiliano Martínez",
        "short_name": "E. Martínez",
        "position": "GK",
        "club": "Aston Villa",
        "league": "ENG-Premier League",
        "statsbomb_name": "Emiliano Martínez",
    },
    {
        "player_name": "Gerónimo Rulli",
        "short_name": "G. Rulli",
        "position": "GK",
        "club": "Olympique Marseille",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Gerónimo Rulli",
    },
    {
        "player_name": "Juan Musso",
        "short_name": "J. Musso",
        "position": "GK",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Juan Musso",
    },
    # ── DEFENDERS (9) ───────────────────────────────────────────────────────
    {
        "player_name": "Gonzalo Montiel",
        "short_name": "G. Montiel",
        "position": "DF",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Gonzalo Montiel",
    },
    {
        "player_name": "Nahuel Molina",
        "short_name": "N. Molina",
        "position": "DF",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Nahuel Molina",
    },
    {
        "player_name": "Lisandro Martínez",
        "short_name": "Li. Martínez",
        "position": "DF",
        "club": "Manchester United",
        "league": "ENG-Premier League",
        "statsbomb_name": "Lisandro Martínez",
    },
    {
        "player_name": "Nicolás Otamendi",
        "short_name": "N. Otamendi",
        "position": "DF",
        "club": "Benfica",
        "league": "POR-Primeira Liga",
        "statsbomb_name": "Nicolás Otamendi",
    },
    {
        "player_name": "Leonardo Balerdi",
        "short_name": "L. Balerdi",
        "position": "DF",
        "club": "Olympique Marseille",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Leonardo Balerdi",
    },
    {
        "player_name": "Cristian Romero",
        "short_name": "C. Romero",
        "position": "DF",
        "club": "Tottenham Hotspur",
        "league": "ENG-Premier League",
        "statsbomb_name": "Cristian Romero",
    },
    {
        "player_name": "Facundo Medina",
        "short_name": "F. Medina",
        "position": "DF",
        "club": "Olympique Marseille",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Facundo Medina",
    },
    {
        "player_name": "Nicolás Tagliafico",
        "short_name": "N. Tagliafico",
        "position": "DF",
        "club": "Olympique Lyonnais",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Nicolás Tagliafico",
    },
    {
        "player_name": "Valentín Barco",
        "short_name": "V. Barco",
        "position": "DF",
        "club": "Strasbourg",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Valentín Barco",
    },
    # ── MIDFIELDERS (7) ─────────────────────────────────────────────────────
    {
        "player_name": "Leandro Paredes",
        "short_name": "L. Paredes",
        "position": "MF",
        "club": "Boca Juniors",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Leandro Paredes",
    },
    {
        "player_name": "Rodrigo De Paul",
        "short_name": "R. De Paul",
        "position": "MF",
        "club": "Inter Miami",
        "league": "USA-Major League Soccer",
        "statsbomb_name": "Rodrigo De Paul",
    },
    {
        "player_name": "Exequiel Palacios",
        "short_name": "E. Palacios",
        "position": "MF",
        "club": "Bayer Leverkusen",
        "league": "GER-Bundesliga",
        "statsbomb_name": "Exequiel Palacios",
    },
    {
        "player_name": "Enzo Fernández",
        "short_name": "E. Fernández",
        "position": "MF",
        "club": "Chelsea",
        "league": "ENG-Premier League",
        "statsbomb_name": "Enzo Fernández",
    },
    {
        "player_name": "Alexis Mac Allister",
        "short_name": "A. Mac Allister",
        "position": "MF",
        "club": "Liverpool",
        "league": "ENG-Premier League",
        "statsbomb_name": "Alexis Mac Allister",
    },
    {
        "player_name": "Giovani Lo Celso",
        "short_name": "G. Lo Celso",
        "position": "MF",
        "club": "Real Betis",
        "league": "ESP-La Liga",
        "statsbomb_name": "Giovani Lo Celso",
    },
    {
        "player_name": "Nicolás Paz",
        "short_name": "N. Paz",
        "position": "MF",
        "club": "Como",
        "league": "ITA-Serie A",
        "statsbomb_name": "Nicolás Paz",
    },
    # ── FORWARDS (7) ────────────────────────────────────────────────────────
    {
        "player_name": "Lionel Messi",
        "short_name": "L. Messi",
        "position": "FW",
        "club": "Inter Miami",
        "league": "USA-Major League Soccer",
        "statsbomb_name": "Lionel Messi",
    },
    {
        "player_name": "Thiago Almada",
        "short_name": "T. Almada",
        "position": "FW",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Thiago Almada",
    },
    {
        "player_name": "Nicolás González",
        "short_name": "N. González",
        "position": "FW",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Nicolás González",
    },
    {
        "player_name": "Giuliano Simeone",
        "short_name": "G. Simeone",
        "position": "FW",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Giuliano Simeone",
    },
    {
        "player_name": "Lautaro Martínez",
        "short_name": "La. Martínez",
        "position": "FW",
        "club": "Internazionale",
        "league": "ITA-Serie A",
        "statsbomb_name": "Lautaro Martínez",
    },
    {
        "player_name": "José Manuel López",
        "short_name": "J. López",
        "position": "FW",
        "club": "Palmeiras",
        "league": "BRA-Série A",
        "statsbomb_name": "José Manuel López",
    },
    {
        "player_name": "Julián Álvarez",
        "short_name": "J. Álvarez",
        "position": "FW",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Julián Álvarez",
    },
]

# Quick sanity assertion — fail loudly at import time if roster size drifts.
assert len(SQUAD) == 26, f"Expected 26 players, got {len(SQUAD)}"

# ---------------------------------------------------------------------------
# League → latest season mapping (soccerdata / FBRef season strings)
# ---------------------------------------------------------------------------
LEAGUE_SEASON: Dict[str, str] = {
    "ENG-Premier League":  "2024-25",
    "ESP-La Liga":         "2024-25",
    "ITA-Serie A":         "2024-25",
    "FRA-Ligue 1":         "2024-25",
    "GER-Bundesliga":      "2024-25",
    "GER-2. Bundesliga":   "2024-25",
    "POR-Primeira Liga":   "2024-25",
    "USA-Major League Soccer": "2025",
    "BRA-Série A":         "2025",
    "ARG-Liga Profesional":"2025",
    "BEL-First Division A":"2024-25",
}

CURRENT_SEASON = "2024-25"

# Big 5 leagues covered by Understat
BIG5_LEAGUES = {
    "ENG-Premier League",
    "ESP-La Liga",
    "ITA-Serie A",
    "FRA-Ligue 1",
    "GER-Bundesliga",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_squad_df() -> pd.DataFrame:
    """Return the full 55-player squad as a tidy DataFrame."""
    return pd.DataFrame(SQUAD)


def get_players_by_league() -> Dict[str, List[str]]:
    """
    Return a dict mapping each league code to a list of player_name strings.

    Example
    -------
    >>> by_league = get_players_by_league()
    >>> by_league["ENG-Premier League"]
    ['Emiliano Martínez', 'Lisandro Martínez', ...]
    """
    result: Dict[str, List[str]] = {}
    for player in SQUAD:
        league = player["league"]
        result.setdefault(league, []).append(player["player_name"])
    return result
