"""
etl/transform/player_name_map.py
---------------------------------
Name mapping dictionaries for resolving raw scraped player names
(FBRef and StatsBomb formats) to canonical player_name values
stored in dim_player.

Also provides a competition name → (type, year) mapping and
a generic resolve_player_name() helper.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# FBRef → canonical player_name
# ---------------------------------------------------------------------------
FBREF_TO_CANONICAL: dict[str, str] = {
    # Goalkeepers
    "Emiliano Martínez": "Emiliano Martínez",
    "E. Martínez": "Emiliano Martínez",
    "Dibu Martínez": "Emiliano Martínez",
    "Gerónimo Rulli": "Gerónimo Rulli",
    "G. Rulli": "Gerónimo Rulli",
    "Walter Benítez": "Walter Benítez",
    "W. Benítez": "Walter Benítez",
    # Defenders
    "Nahuel Molina": "Nahuel Molina",
    "N. Molina": "Nahuel Molina",
    "Gonzalo Montiel": "Gonzalo Montiel",
    "G. Montiel": "Gonzalo Montiel",
    "Cristian Romero": "Cristian Romero",
    "C. Romero": "Cristian Romero",
    "Cuti Romero": "Cristian Romero",
    "Lisandro Martínez": "Lisandro Martínez",
    "Li. Martínez": "Lisandro Martínez",
    "Germán Pezzella": "Germán Pezzella",
    "G. Pezzella": "Germán Pezzella",
    "Nicolás Tagliafico": "Nicolás Tagliafico",
    "N. Tagliafico": "Nicolás Tagliafico",
    "Facundo Medina": "Facundo Medina",
    "F. Medina": "Facundo Medina",
    "Nicolás Otamendi": "Nicolás Otamendi",
    "N. Otamendi": "Nicolás Otamendi",
    "Marcos Acuña": "Marcos Acuña",
    "M. Acuña": "Marcos Acuña",
    # Midfielders
    "Rodrigo De Paul": "Rodrigo De Paul",
    "R. De Paul": "Rodrigo De Paul",
    "Leandro Paredes": "Leandro Paredes",
    "L. Paredes": "Leandro Paredes",
    "Alexis Mac Allister": "Alexis Mac Allister",
    "A. Mac Allister": "Alexis Mac Allister",
    "Enzo Fernández": "Enzo Fernández",
    "E. Fernández": "Enzo Fernández",  # default: Enzo (not Exequiel)
    "Exequiel Palacios": "Exequiel Palacios",
    "E. Palacios": "Exequiel Palacios",
    "Guido Rodríguez": "Guido Rodríguez",
    "G. Rodríguez": "Guido Rodríguez",
    "Giovani Lo Celso": "Giovani Lo Celso",
    "G. Lo Celso": "Giovani Lo Celso",
    "Nicolás González": "Nicolás González",
    "N. González": "Nicolás González",
    "Thiago Almada": "Thiago Almada",
    "T. Almada": "Thiago Almada",
    "Nicolás Paz": "Nicolás Paz",
    "N. Paz": "Nicolás Paz",
    "Nico Paz": "Nicolás Paz",   # Understat uses this short form
    # Forwards
    "Lionel Messi": "Lionel Messi",
    "L. Messi": "Lionel Messi",
    "Ángel Di María": "Ángel Di María",
    "Á. Di María": "Ángel Di María",
    "A. Di María": "Ángel Di María",
    "Lautaro Martínez": "Lautaro Martínez",
    "L. Martínez": "Lautaro Martínez",  # careful: Lisandro uses "Li." abbreviation
    "Julián Álvarez": "Julián Álvarez",
    "J. Álvarez": "Julián Álvarez",
    "Paulo Dybala": "Paulo Dybala",
    "P. Dybala": "Paulo Dybala",
    "Joaquín Correa": "Joaquín Correa",
    "J. Correa": "Joaquín Correa",
    "Alejandro Garnacho": "Alejandro Garnacho",
    "A. Garnacho": "Alejandro Garnacho",
    "Valentín Carboni": "Valentín Carboni",
    "V. Carboni": "Valentín Carboni",
}

# ---------------------------------------------------------------------------
# StatsBomb → canonical player_name
# ---------------------------------------------------------------------------
STATSBOMB_TO_CANONICAL: dict[str, str] = {
    # Goalkeepers
    "Emiliano Martínez": "Emiliano Martínez",
    "Emiliano Martínez Romero": "Emiliano Martínez",
    "Damián Emiliano Martínez": "Emiliano Martínez",
    "Gerónimo Rulli": "Gerónimo Rulli",
    "Walter Néstor Benítez": "Walter Benítez",
    "Walter Benítez": "Walter Benítez",
    # Defenders
    "Gonzalo Montiel": "Gonzalo Montiel",
    "Gonzalo Ariel Montiel": "Gonzalo Montiel",
    "Nahuel Molina": "Nahuel Molina",
    "Nahuel Molina Lucero": "Nahuel Molina",
    "Lisandro Martínez": "Lisandro Martínez",
    "Nicolás Otamendi": "Nicolás Otamendi",
    "Nicolás Hernán Otamendi": "Nicolás Otamendi",
    "Leonardo Balerdi": "Leonardo Balerdi",
    "Cristian Romero": "Cristian Romero",
    "Cristian Gabriel Romero": "Cristian Romero",
    "Facundo Medina": "Facundo Medina",
    "Nicolás Tagliafico": "Nicolás Tagliafico",
    "Nicolás Alejandro Tagliafico": "Nicolás Tagliafico",
    "Valentín Barco": "Valentín Barco",
    "Germán Pezzella": "Germán Pezzella",
    "Marcos Acuña": "Marcos Acuña",
    # Midfielders
    "Leandro Paredes": "Leandro Paredes",
    "Leandro Daniel Paredes": "Leandro Paredes",
    "Rodrigo De Paul": "Rodrigo De Paul",
    "Rodrigo Javier De Paul": "Rodrigo De Paul",
    "Exequiel Palacios": "Exequiel Palacios",
    "Enzo Fernández": "Enzo Fernández",
    "Enzo Fernandez": "Enzo Fernández",
    "Alexis Mac Allister": "Alexis Mac Allister",
    "Giovani Lo Celso": "Giovani Lo Celso",
    "Guido Rodríguez": "Guido Rodríguez",
    "Nicolás Paz": "Nicolás Paz",
    "Thiago Almada": "Thiago Almada",
    # Forwards
    "Lionel Andrés Messi Cuccittini": "Lionel Messi",
    "Lionel Messi": "Lionel Messi",
    "Julián Álvarez": "Julián Álvarez",
    "Lautaro Martínez": "Lautaro Martínez",
    "Lautaro Javier Martínez": "Lautaro Martínez",
    "Nicolás González": "Nicolás González",
    "Nicolás Iván González": "Nicolás González",
    "Giuliano Simeone": "Giuliano Simeone",
    "Thiago Almada": "Thiago Almada",
    "José Manuel López": "José Manuel López",
    "Ángel Di María": "Ángel Di María",
    "Ángel Fabián Di María": "Ángel Di María",
    "Ángel Fabián Di María Hernández": "Ángel Di María",
    "Paulo Dybala": "Paulo Dybala",
    "Joaquín Correa": "Joaquín Correa",
    "Alejandro Garnacho": "Alejandro Garnacho",
    "Valentín Carboni": "Valentín Carboni",
}

# ---------------------------------------------------------------------------
# Competition name → (type, year or None)
# year=None means it must be inferred from the data
# ---------------------------------------------------------------------------
COMPETITION_MAP: dict[str, tuple[str, int | None]] = {
    "FIFA World Cup": ("WC", None),
    "World Cup": ("WC", None),
    "Copa América": ("CA", None),
    "Copa America": ("CA", None),
    "Copa América 2021": ("CA", 2021),
    "Copa América 2024": ("CA", 2024),
    "World Cup Qualifying - CONMEBOL": ("WCQ", None),   # year inferred from match dates
    "World Cup Qualifying 2022 - CONMEBOL": ("WCQ", None),
    "WCQ - CONMEBOL": ("WCQ", None),
    "CONMEBOL World Cup Qualifying": ("WCQ", None),
    "Friendlies (M)": ("FRIENDLY", None),
    "International Friendlies": ("FRIENDLY", None),
    "Friendlies": ("FRIENDLY", None),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_player_name(raw_name: str, mapping: dict[str, str]) -> str | None:
    """
    Resolve a raw scraped name to a canonical player_name.

    Resolution order:
      1. Direct dict lookup (exact match).
      2. Normalize-based lookup (strips accents, lowercases, collapses spaces).

    Returns the canonical name string, or None if no mapping found.
    """
    if not isinstance(raw_name, str):
        return None

    # 1. Direct lookup
    if raw_name in mapping:
        return mapping[raw_name]

    # 2. Normalise-based lookup
    from etl.extract.utils import normalize_name

    norm_raw = normalize_name(raw_name)
    for key, canonical in mapping.items():
        if normalize_name(key) == norm_raw:
            return canonical

    return None
