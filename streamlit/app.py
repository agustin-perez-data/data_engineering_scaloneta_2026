import streamlit as st

st.set_page_config(
    page_title="Scaloneta 2026 — Argentina Dashboard",
    page_icon="🇦🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Argentine blue/white/gold theme via custom CSS
st.markdown(
    """
<style>
/* Fuente con soporte completo de caracteres latinos: ñ, á, é, í, ó, ú, ü */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif !important;
}
[data-testid="stSidebar"] { background: #003087; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stRadio label { color: white !important; }
h1, h2, h3 { color: #74ACDF; }
.metric-container { border-left: 4px solid #F6B40E; padding-left: 12px; }
[data-testid="metric-container"] {
    border-left: 4px solid #F6B40E;
    padding-left: 12px;
    background: #0d1117;
    border-radius: 4px;
}
[data-testid="metric-container"] label { color: #74ACDF !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2rem; }
.stApp { background-color: #0d1117; color: #FFFFFF; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🇦🇷 Scaloneta al Mundial 2026")
st.markdown(
    "**Análisis de la Selección Argentina** — Desde Qatar 2022 al camino al Mundial 2026"
)

col1, col2, col3, col4 = st.columns(4)

try:
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    from db import query

    summary = query("""
        SELECT
            COUNT(*)                                              AS matches,
            SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END)       AS wins,
            SUM(goals_for)                                        AS goals_scored,
            SUM(goals_against)                                    AS goals_conceded
        FROM fact_match
    """)
    if not summary.empty:
        row = summary.iloc[0]
        col1.metric("Partidos jugados", int(row["matches"]))
        col2.metric("Victorias", int(row["wins"]))
        col3.metric("Goles a favor", int(row["goals_scored"]))
        col4.metric("Goles en contra", int(row["goals_conceded"]))
    else:
        for col, label in zip(
            [col1, col2, col3, col4],
            ["Partidos jugados", "Victorias", "Goles a favor", "Goles en contra"],
        ):
            col.metric(label, "—")
except Exception:
    for col, label in zip(
        [col1, col2, col3, col4],
        ["Partidos jugados", "Victorias", "Goles a favor", "Goles en contra"],
    ):
        col.metric(label, "—")
    st.info(
        "Conectá la base de datos y ejecutá el ETL para ver los datos reales."
    )

st.markdown("---")

st.markdown(
    """
### Secciones disponibles

| Sección | Descripción |
|---|---|
| 📅 **Partidos** | Historial de partidos, resultados, xG y estadísticas por competencia |
| 👤 **Jugadores** | Análisis individual, comparación radar, heatmaps y evolución temporal |

Navegá por las secciones en el menú lateral 👈
"""
)
