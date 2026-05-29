import streamlit as st

st.set_page_config(
    page_title="Scaloneta 2026",
    page_icon="🇦🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Fuente global ─────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif !important;
}

/* ── Ocultar deploy button y menú de 3 puntos ──────────── */
#MainMenu                                    { display: none !important; }
[data-testid="stDeployButton"]               { display: none !important; }
.stDeployButton                              { display: none !important; }
[data-testid="stToolbarActions"]             { display: none !important; }
/* Header transparente pero visible para que el botón del sidebar funcione */
header[data-testid="stHeader"]               { background: transparent !important; }
/* Asegurar que el botón de abrir/cerrar sidebar sea siempre visible */
[data-testid="collapsedControl"]             { display: flex !important; visibility: visible !important; }
[data-testid="stSidebarCollapsedControl"]    { display: flex !important; visibility: visible !important; }

/* ── Fondo principal — azul noche argentina ─────────────── */
.stApp {
    background: linear-gradient(160deg, #050f1c 0%, #0b1f3a 50%, #071428 100%);
    color: #FFFFFF;
}
[data-testid="stAppViewContainer"] {
    background: transparent;
}
[data-testid="stMain"] {
    background: transparent;
}

/* ── Sidebar — celeste a azul, estilo camiseta ──────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #001845 0%, #003087 35%, #74ACDF 100%) !important;
    border-right: 2px solid #74ACDF;
}
[data-testid="stSidebar"] * { color: white !important; }

/* ── Títulos ────────────────────────────────────────────── */
h1, h2, h3 { color: #74ACDF; }

/* ── Métricas ───────────────────────────────────────────── */
[data-testid="metric-container"] {
    border-left: 4px solid #F6B40E;
    padding-left: 12px;
    background: rgba(116, 172, 223, 0.07);
    border-radius: 6px;
}
[data-testid="metric-container"] label {
    color: #74ACDF !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 2rem;
}

/* ── Selectbox / inputs ─────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(116, 172, 223, 0.08) !important;
    border: 1px solid #74ACDF !important;
    color: white !important;
}

/* ── Menú de navegación — botones más grandes ───────────── */
[data-testid="stSidebarNavLink"] {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    padding: 14px 20px !important;
    line-height: 1.8 !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
}
[data-testid="stSidebarNavLink"] span,
[data-testid="stSidebarNavLink"] p {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
}
section[data-testid="stSidebar"] nav ul li a,
section[data-testid="stSidebar"] nav a {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    padding: 12px 16px !important;
}
</style>
""", unsafe_allow_html=True)

from i18n import render_lang_toggle

render_lang_toggle()

pg = st.navigation([
    st.Page("pages/03_Shot_Map.py",  title="Shot Map",  icon="🎯"),
    st.Page("pages/04_Heatmap.py",   title="Heat Map",  icon="🔥"),
    st.Page("pages/05_Pass_Map.py",  title="Pass Map",  icon="🔵"),
])
pg.run()
