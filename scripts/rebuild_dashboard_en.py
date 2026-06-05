# -*- coding: utf-8 -*-
"""
scripts/rebuild_dashboard_en.py
Reconstruye los dashboards EN copiando exactamente los ES, traduciendo SQL y títulos.
"""
import sys
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MB       = "http://143.198.177.104:3000"
EMAIL    = "agustinezequielperez27@gmail.com"
PASSWORD = "Perrogato3"

DASHBOARD_PAIRS = [
    ("Plantel 2024-25 — Club Stats",        "2024-25 Squad — Club Stats"),
    ("Selección — Historial de Resultados",  "National Team — Match Results"),
    ("Selección — Rendimiento Individual",   "National Team — Individual Performance"),
]

# ── Traducciones ──────────────────────────────────────────────────────────────

SQL_TRANSLATIONS = {
    'AS "Jugador"':          'AS "Player"',
    'AS "Posición"':         'AS "Position"',
    'AS "Partidos"':         'AS "Matches"',
    'AS "Goles"':            'AS "Goals"',
    'AS "Asistencias"':      'AS "Assists"',
    'AS "Disparos"':         'AS "Shots"',
    'AS "Barridas"':         'AS "Tackles"',
    'AS "Intercepciones"':   'AS "Interceptions"',
    'AS "Competencia"':      'AS "Competition"',
    'AS "Contribuciones"':   'AS "Contributions"',
    'AS "Goles x partido"':  'AS "Goals per match"',
    'AS jugador':            'AS player',
    'AS posicion':           'AS position',
    'AS competencia':        'AS competition',
    'AS partidos':           'AS matches',
}

TITLE_TRANSLATIONS = {
    # Rendimiento Individual
    "Máximo goleador en selección":                  "Top Scorer in NT",
    "Más partidos jugados en selección":             "Most Appearances in NT",
    "Más barridas en selección":                     "Most Tackles in NT",
    "Estadísticas Individuales":                     "Individual Statistics",
    "Participación por Competencia":                 "Participation by Competition",
    "Rendimiento Ofensivo — Goles vs xG":            "Offensive Performance — Goals vs xG",
    " Rendimiento Ofensivo — Goles vs xG":           " Offensive Performance — Goals vs xG",
    "Contribuciones Ofensivas por Posición":         "Offensive Contributions by Position",
    # Plantel
    "Goles del plantel (total)":                     "Squad Goals (total)",
    "xG total del plantel":                          "Squad total xG",
    "Promedio pass%":                                "Avg pass%",
    "Promedio tackles":                              "Avg tackles",
    "Plantel completo — Stats 2024-25":              "Full Squad — 2024-25 Stats",
    "Goles vs xG — Sobre/bajo rendimiento":          "Goals vs xG — Over/underperformers",
    "Goles + Asistencias por jugador":               "Goals + Assists per player",
    "Tackles + Interceptions por jugador":           "Tackles + Interceptions per player",
    # Resultados
    "Total partidos":                                "Total matches",
    "Victorias":                                     "Wins",
    "% Victorias":                                   "Win rate",
    "Goles a favor":                                 "Goals scored",
    "Goles en contra":                               "Goals conceded",
    "Todos los partidos":                            "All matches",
    "W / E / D por competencia":                     "W / D / L by competition",
    "Goles a favor vs en contra (por partido)":      "Goals scored vs conceded (per match)",
    "Record vs rivales frecuentes (≥ 2 partidos)":   "Record vs frequent opponents (≥ 2 matches)",
}

TAG_DISPLAY_TRANSLATIONS = {
    "Posición":    "Position",
    "Competencia": "Competition",
    "Jugador":     "Player",
}

PARAM_NAME_TRANSLATIONS = {
    "Posición":    "Position",
    "Posicion":    "Position",
    "Competencia": "Competition",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def translate_sql(sql):
    for es, en in SQL_TRANSLATIONS.items():
        sql = sql.replace(es, en)
    return sql


def translate_title(title):
    return TITLE_TRANSLATIONS.get(title, title)


def translate_template_tags(tags):
    result = {}
    for key, tag in tags.items():
        new_tag = dict(tag)
        display = new_tag.get("display-name", "")
        new_tag["display-name"] = TAG_DISPLAY_TRANSLATIONS.get(display, display)
        dim = new_tag.get("dimension")
        if isinstance(dim, list) and len(dim) == 3 and isinstance(dim[1], dict):
            new_tag["dimension"] = ["field", dim[2], None]
        result[key] = new_tag
    return result


def translate_params(params):
    result = []
    for p in params:
        new_p = dict(p)
        new_p["name"] = PARAM_NAME_TRANSLATIONS.get(p.get("name", ""), p.get("name", ""))
        result.append(new_p)
    return result


def get_size(dc, axis):
    new_key = f"size_{axis}"
    old_key = f"size{axis.upper()}"
    return dc.get(new_key) or dc.get(old_key) or (8 if axis == "x" else 4)


def rebuild_pair(es_name, en_name, name_to_id):
    es_id = name_to_id.get(es_name)
    en_id = name_to_id.get(en_name)

    if not es_id:
        print(f"  ✗ No encontrado: '{es_name}'")
        return
    if not en_id:
        print(f"  ✗ No encontrado: '{en_name}'")
        return

    print(f"  ES → ID={es_id} | EN → ID={en_id}")

    es_dash         = requests.get(f"{MB}/api/dashboard/{es_id}", headers=HDR).json()
    es_params       = es_dash.get("parameters", [])
    es_cards_sorted = sorted(es_dash.get("dashcards", []),
                             key=lambda x: (x["row"], x["col"]))

    print(f"  Cards: {len(es_cards_sorted)} | Filtros: {[p['name'] for p in es_params]}\n")

    new_dashcards = []

    for dc in es_cards_sorted:
        es_card       = requests.get(f"{MB}/api/card/{dc['card_id']}", headers=HDR).json()
        old_title     = es_card.get("name", "")
        new_title     = translate_title(old_title)
        dataset_query = es_card.get("dataset_query", {})
        db_id         = dataset_query.get("database", 2)

        stages = dataset_query.get("stages", [])
        if stages:
            stage    = stages[0]
            old_sql  = stage.get("native", "")
            old_tags = stage.get("template-tags", {})
        else:
            native   = dataset_query.get("native", {})
            old_sql  = native.get("query", "")
            old_tags = native.get("template-tags", {})

        new_sql  = translate_sql(old_sql)
        new_tags = translate_template_tags(old_tags)

        payload = {
            "name":                   new_title,
            "dataset_query":          {"type": "native", "database": db_id,
                                       "native": {"query": new_sql, "template-tags": new_tags}},
            "display":                es_card.get("display", "table"),
            "visualization_settings": es_card.get("visualization_settings", {}),
            "description":            es_card.get("description"),
        }

        r = requests.post(f"{MB}/api/card", headers=HDR, json=payload)
        if r.status_code not in (200, 202):
            print(f"    ✗ Error creando '{new_title}': {r.status_code} — {r.text[:100]}")
            continue

        new_card_id = r.json()["id"]
        print(f"    ✓ [{new_card_id:4d}] '{old_title}' → '{new_title}'")

        updated_mappings = []
        for m in dc.get("parameter_mappings", []):
            target = m.get("target", [])
            if isinstance(target, list) and len(target) == 3 and isinstance(target[2], dict):
                target = target[:2]
            updated_mappings.append({**m, "card_id": new_card_id, "target": target})

        new_dashcards.append({
            "id":                     -(len(new_dashcards) + 1),
            "card_id":                new_card_id,
            "row":                    dc["row"],
            "col":                    dc["col"],
            "size_x":                 get_size(dc, "x"),
            "size_y":                 get_size(dc, "y"),
            "parameter_mappings":     updated_mappings,
            "visualization_settings": {},
        })

    print(f"\n  Actualizando dashboard EN con {len(new_dashcards)} cards...")
    r = requests.put(f"{MB}/api/dashboard/{en_id}", headers=HDR, json={
        "dashcards":  new_dashcards,
        "parameters": translate_params(es_params),
    })

    if r.status_code == 200:
        loaded = len(r.json().get("dashcards", []))
        print(f"  ✅ {loaded} cards cargadas → http://143.198.177.104:3000/dashboard/{en_id}")
    else:
        print(f"  ✗ Error {r.status_code}: {r.text[:300]}")


# ── Auth ──────────────────────────────────────────────────────────────────────

print("Autenticando en Metabase producción...")
r = requests.post(f"{MB}/api/session",
                  json={"username": EMAIL, "password": PASSWORD})
r.raise_for_status()
token = r.json()["id"]
HDR = {"X-Metabase-Session": token}
print("✓ Autenticado\n")

all_dashboards = requests.get(f"{MB}/api/dashboard", headers=HDR).json()
name_to_id = {d["name"]: d["id"] for d in all_dashboards}

# ── Procesar todos los pares ──────────────────────────────────────────────────

for es_name, en_name in DASHBOARD_PAIRS:
    print(f"\n{'='*60}")
    print(f"  {es_name}")
    print(f"  → {en_name}")
    print(f"{'='*60}")
    rebuild_pair(es_name, en_name, name_to_id)

print("\n✅ Listo.")
