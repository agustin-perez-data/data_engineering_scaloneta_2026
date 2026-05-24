"""
Squad configuration for Argentina national team — 2026 World Cup cycle.
55-player extended squad covering all positions and clubs.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

# ---------------------------------------------------------------------------
# Full squad  (6 GK + 19 DF + 15 MF + 15 FW = 55)
# Keys
#   player_name    : full name with accents
#   short_name     : nickname / abbreviated name used in displays
#   position       : GK | DF | MF | FW
#   club           : current club (long-form)
#   league         : soccerdata / FBRef league code
#   statsbomb_name : name as it appears in StatsBomb open-data
# ---------------------------------------------------------------------------
SQUAD: List[Dict[str, str]] = [
    # ── GOALKEEPERS (6) ─────────────────────────────────────────────────────
    {
        "player_name": "Emiliano Martínez",
        "short_name": "Dibu Martínez",
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
    {
        "player_name": "Walter Benítez",
        "short_name": "W. Benítez",
        "position": "GK",
        "club": "Crystal Palace",
        "league": "ENG-Premier League",
        "statsbomb_name": "Walter Benítez",
    },
    {
        "player_name": "Facundo Cambeses",
        "short_name": "F. Cambeses",
        "position": "GK",
        "club": "Racing Club",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Facundo Cambeses",
    },
    {
        "player_name": "Santiago Beltrán",
        "short_name": "S. Beltrán",
        "position": "GK",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Santiago Beltrán",
    },
    # ── DEFENDERS (19) ──────────────────────────────────────────────────────
    {
        "player_name": "Agustín Giay",
        "short_name": "A. Giay",
        "position": "DF",
        "club": "Palmeiras",
        "league": "BRA-Série A",
        "statsbomb_name": "Agustín Giay",
    },
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
        "player_name": "Nicolás Capaldo",
        "short_name": "N. Capaldo",
        "position": "DF",
        "club": "Hamburger SV",
        "league": "GER-2. Bundesliga",
        "statsbomb_name": "Nicolás Capaldo",
    },
    {
        "player_name": "Kevin Mac Allister",
        "short_name": "K. Mac Allister",
        "position": "DF",
        "club": "Union Saint-Gilloise",
        "league": "BEL-First Division A",
        "statsbomb_name": "Kevin Mac Allister",
    },
    {
        "player_name": "Lucas Martínez Quarta",
        "short_name": "L. Martínez Quarta",
        "position": "DF",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Lucas Martínez Quarta",
    },
    {
        "player_name": "Marcos Senesi",
        "short_name": "M. Senesi",
        "position": "DF",
        "club": "Bournemouth",
        "league": "ENG-Premier League",
        "statsbomb_name": "Marcos Senesi",
    },
    {
        "player_name": "Lisandro Martínez",
        "short_name": "L. Martínez",
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
        "player_name": "Germán Pezzella",
        "short_name": "G. Pezzella",
        "position": "DF",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Germán Pezzella",
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
        "short_name": "Cuti Romero",
        "position": "DF",
        "club": "Tottenham Hotspur",
        "league": "ENG-Premier League",
        "statsbomb_name": "Cristian Romero",
    },
    {
        "player_name": "Lautaro Di Lollo",
        "short_name": "L. Di Lollo",
        "position": "DF",
        "club": "Boca Juniors",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Lautaro Di Lollo",
    },
    {
        "player_name": "Zaid Romero",
        "short_name": "Z. Romero",
        "position": "DF",
        "club": "Getafe",
        "league": "ESP-La Liga",
        "statsbomb_name": "Zaid Romero",
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
        "player_name": "Marcos Acuña",
        "short_name": "Huevo Acuña",
        "position": "DF",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Marcos Acuña",
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
        "player_name": "Gabriel Rojas",
        "short_name": "G. Rojas",
        "position": "DF",
        "club": "Racing Club",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Gabriel Rojas",
    },
    {
        "player_name": "Valentín Barco",
        "short_name": "El Colo Barco",
        "position": "DF",
        "club": "Strasbourg",
        "league": "FRA-Ligue 1",
        "statsbomb_name": "Valentín Barco",
    },
    # ── MIDFIELDERS (15) ────────────────────────────────────────────────────
    {
        "player_name": "Máximo Perrone",
        "short_name": "M. Perrone",
        "position": "MF",
        "club": "Como",
        "league": "ITA-Serie A",
        "statsbomb_name": "Máximo Perrone",
    },
    {
        "player_name": "Leandro Paredes",
        "short_name": "L. Paredes",
        "position": "MF",
        "club": "Boca Juniors",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Leandro Paredes",
    },
    {
        "player_name": "Guido Rodríguez",
        "short_name": "G. Rodríguez",
        "position": "MF",
        "club": "Valencia",
        "league": "ESP-La Liga",
        "statsbomb_name": "Guido Rodríguez",
    },
    {
        "player_name": "Aníbal Moreno",
        "short_name": "A. Moreno",
        "position": "MF",
        "club": "River Plate",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Aníbal Moreno",
    },
    {
        "player_name": "Milton Delgado",
        "short_name": "M. Delgado",
        "position": "MF",
        "club": "Boca Juniors",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Milton Delgado",
    },
    {
        "player_name": "Alan Varela",
        "short_name": "A. Varela",
        "position": "MF",
        "club": "Porto",
        "league": "POR-Primeira Liga",
        "statsbomb_name": "Alan Varela",
    },
    {
        "player_name": "Ezequiel Fernández",
        "short_name": "E. Fernández",
        "position": "MF",
        "club": "Bayer Leverkusen",
        "league": "GER-Bundesliga",
        "statsbomb_name": "Ezequiel Fernández",
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
        "short_name": "Enzo Fernández",
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
        "player_name": "Nicolás Domínguez",
        "short_name": "N. Domínguez",
        "position": "MF",
        "club": "Nottingham Forest",
        "league": "ENG-Premier League",
        "statsbomb_name": "Nicolás Domínguez",
    },
    {
        "player_name": "Emiliano Buendía",
        "short_name": "E. Buendía",
        "position": "MF",
        "club": "Aston Villa",
        "league": "ENG-Premier League",
        "statsbomb_name": "Emiliano Buendía",
    },
    {
        "player_name": "Nicolás Paz",
        "short_name": "Nico Paz",
        "position": "MF",
        "club": "Como",
        "league": "ITA-Serie A",
        "statsbomb_name": "Nicolás Paz",
    },
    # ── FORWARDS (15) ───────────────────────────────────────────────────────
    {
        "player_name": "Lionel Messi",
        "short_name": "Messi",
        "position": "FW",
        "club": "Inter Miami",
        "league": "USA-Major League Soccer",
        "statsbomb_name": "Lionel Messi",
    },
    {
        "player_name": "Franco Mastantuono",
        "short_name": "F. Mastantuono",
        "position": "FW",
        "club": "Real Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Franco Mastantuono",
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
        "player_name": "Tomás Aranda",
        "short_name": "T. Aranda",
        "position": "FW",
        "club": "Boca Juniors",
        "league": "ARG-Liga Profesional",
        "statsbomb_name": "Tomás Aranda",
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
        "player_name": "Alejandro Garnacho",
        "short_name": "Garnacho",
        "position": "FW",
        "club": "Chelsea",
        "league": "ENG-Premier League",
        "statsbomb_name": "Alejandro Garnacho",
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
        "player_name": "Matías Soulé",
        "short_name": "M. Soulé",
        "position": "FW",
        "club": "AS Roma",
        "league": "ITA-Serie A",
        "statsbomb_name": "Matías Soulé",
    },
    {
        "player_name": "Claudio Echeverri",
        "short_name": "C. Echeverri",
        "position": "FW",
        "club": "Girona",
        "league": "ESP-La Liga",
        "statsbomb_name": "Claudio Echeverri",
    },
    {
        "player_name": "Gianluca Prestianni",
        "short_name": "G. Prestianni",
        "position": "FW",
        "club": "Benfica",
        "league": "POR-Primeira Liga",
        "statsbomb_name": "Gianluca Prestianni",
    },
    {
        "player_name": "Santiago Castro",
        "short_name": "S. Castro",
        "position": "FW",
        "club": "Bologna",
        "league": "ITA-Serie A",
        "statsbomb_name": "Santiago Castro",
    },
    {
        "player_name": "Lautaro Martínez",
        "short_name": "El Toro",
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
        "short_name": "La Araña",
        "position": "FW",
        "club": "Atlético Madrid",
        "league": "ESP-La Liga",
        "statsbomb_name": "Julián Álvarez",
    },
    {
        "player_name": "Mateo Pellegrino",
        "short_name": "M. Pellegrino",
        "position": "FW",
        "club": "Parma",
        "league": "ITA-Serie A",
        "statsbomb_name": "Mateo Pellegrino",
    },
]

# Quick sanity assertion — fail loudly at import time if roster size drifts.
assert len(SQUAD) == 55, f"Expected 55 players, got {len(SQUAD)}"

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
    ['Emiliano Martínez', 'Walter Benítez', ...]
    """
    result: Dict[str, List[str]] = {}
    for player in SQUAD:
        league = player["league"]
        result.setdefault(league, []).append(player["player_name"])
    return result
