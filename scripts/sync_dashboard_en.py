"""
scripts/sync_dashboard_en.py
Sincroniza el dashboard EN con los cambios hechos en el dashboard ES.
Conecta a producción: http://143.198.177.104:3000
Matchea cards por posición (row, col) — misma estructura en ambos dashboards.
"""
import requests

MB       = "http://143.198.177.104:3000"
EMAIL    = "agustinezequielperez27@gmail.com"
PASSWORD = "Perrogato3"

ES_NAME = "Selección — Rendimiento Individual"
EN_NAME = "National Team — Individual Performance"

SQL_TRANSLATIONS = {
    '"Jugador"':              '"Player"',
    '"Posición"':             '"Position"',
    '"Partidos"':             '"Matches"',
    '"Goles"':                '"Goals"',
    '"Asistencias"':          '"Assists"',
    '"Disparos"':             '"Shots"',
    '"Barridas"':             '"Tackles"',
    '"Intercepciones"':       '"Interceptions"',
    '"Competencia"':          '"Competition"',
    '"Contribuciones"':       '"Contributions"',
    '"Goles x partido"':      '"Goals per match"',
    'AS competencia':         'AS competition',
    'AS jugador':             'AS player',
    'AS posicion':            'AS position',
}

TITLE_TRANSLATIONS = {
    "Estadísticas Individuales":                "Individual Statistics",
    "Participación por Competencia":            "Participation by Competition",
    "Rendimiento Ofensivo — Goles vs xG":       "Offensive Performance — Goals vs xG",
    "Contribuciones Ofensivas por Posición":    "Offensive Contributions by Position",
    "Máximo goleador en selección":             "Top Scorer in NT",
    "Más partidos jugados en selección":        "Most Appearances in NT",
    "Más barridas en selección":                "Most Tackles in NT",
    "Stats individuales en selección — todas las competencias": "Individual NT stats — all competitions",
    "Partidos Jugados":                         "Matches Played",
    "Goles y xG por jugador en selección":      "Goals and xG per player in NT",
    "Partidos jugados en selección":            "Matches played in NT",
}


def translate_sql(sql):
    for es, en in SQL_TRANSLATIONS.items():
        sql = sql.replace(es, en)
    return sql


def translate_title(title):
    return TITLE_TRANSLATIONS.get(title, title)


# ── Auth ──────────────────────────────────────────────────────────────────────
print("Autenticando en Metabase producción...")
resp = requests.post(f"{MB}/api/session",
                     json={"username": EMAIL, "password": PASSWORD})
resp.raise_for_status()
token = resp.json()["id"]
HDR = {"X-Metabase-Session": token}
print("✓ Autenticado\n")

# ── Encontrar dashboards ──────────────────────────────────────────────────────
all_dashboards = requests.get(f"{MB}/api/dashboard", headers=HDR).json()
es_id = en_id = None
for d in all_dashboards:
    if d["name"] == ES_NAME:
        es_id = d["id"]
    if d["name"] == EN_NAME:
        en_id = d["id"]

if not es_id:
    raise RuntimeError(f"No se encontró el dashboard ES: '{ES_NAME}'")
if not en_id:
    raise RuntimeError(f"No se encontró el dashboard EN: '{EN_NAME}'")

print(f"Dashboard ES: ID={es_id}  ({ES_NAME})")
print(f"Dashboard EN: ID={en_id}  ({EN_NAME})\n")

# ── Obtener dashcards de ambos ────────────────────────────────────────────────
es_dash = requests.get(f"{MB}/api/dashboard/{es_id}", headers=HDR).json()
en_dash = requests.get(f"{MB}/api/dashboard/{en_id}", headers=HDR).json()

es_cards = {(dc["row"], dc["col"]): dc for dc in es_dash["dashcards"]}
en_cards = {(dc["row"], dc["col"]): dc for dc in en_dash["dashcards"]}

print(f"Cards encontradas — ES: {len(es_cards)}, EN: {len(en_cards)}\n")

# ── Sincronizar card por card ─────────────────────────────────────────────────
updated = skipped = errors = 0

for pos, es_dc in sorted(es_cards.items()):
    en_dc = en_cards.get(pos)
    if not en_dc:
        print(f"  ⚠️  Sin match EN en posición {pos} — saltando")
        skipped += 1
        continue

    es_card_id = es_dc["card_id"]
    en_card_id = en_dc["card_id"]

    es_card = requests.get(f"{MB}/api/card/{es_card_id}", headers=HDR).json()
    en_card = requests.get(f"{MB}/api/card/{en_card_id}", headers=HDR).json()

    query = es_card.get("dataset_query", {}).get("native", {}).get("query", "")
    if not query:
        print(f"  ⚠️  Card ES {es_card_id} sin SQL — saltando")
        skipped += 1
        continue

    new_title = translate_title(es_card.get("name", ""))
    new_query = translate_sql(query)

    # Preservar template_tags del EN (field filters ya configurados)
    en_native = en_card.get("dataset_query", {}).get("native", {})
    en_card["dataset_query"]["native"]["query"] = new_query

    r = requests.put(f"{MB}/api/card/{en_card_id}", headers=HDR, json={
        "name":                   new_title,
        "dataset_query":          en_card["dataset_query"],
        "display":                en_card.get("display", "table"),
        "visualization_settings": en_card.get("visualization_settings", {}),
    })

    if r.status_code == 200:
        print(f"  ✓  {pos}  '{es_card.get('name')}' → '{new_title}'")
        updated += 1
    else:
        print(f"  ✗  {pos}  Error {r.status_code}: {r.text[:120]}")
        errors += 1

# ── Resumen ───────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"✅ Cards actualizadas : {updated}")
print(f"⚠️  Saltadas          : {skipped}")
print(f"✗  Errores            : {errors}")
print(f"\nDashboard EN → http://143.198.177.104:3000/dashboard/{en_id}")
