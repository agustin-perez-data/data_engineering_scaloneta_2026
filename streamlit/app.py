import streamlit as st

st.set_page_config(
    page_title="Scaloneta 2026",
    page_icon="🇦🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ==========================================================
   FUENTE GLOBAL
   ========================================================== */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ==========================================================
   OCULTAR ELEMENTOS STREAMLIT
   ========================================================== */
#MainMenu {display:none !important;}
footer {display:none !important;}

[data-testid="stDeployButton"],
[data-testid="stAppDeployButton"],
.stDeployButton,
.stAppDeployButton,
[data-testid="stToolbarActions"],
[data-testid="stBaseButton-header"],
button[aria-label="Deploy"],
button[data-testid="stBaseButton-header"] {
    display:none !important;
}

header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}

/* Breadcrumb "app" y toolbar de navegación */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stAppName"],
[data-testid="stBreadcrumbs"] {
    display: none !important;
}

[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"] {
    display:flex !important;
    visibility:visible !important;
}

/* Botón expand sidebar (cuando está cerrado) — fondo negro */
button[data-testid="stExpandSidebarButton"] {
    background-color: #000000 !important;
    border: none !important;
    border-radius: 0 6px 6px 0 !important;
}

button[data-testid="stExpandSidebarButton"]:hover {
    background-color: #222222 !important;
}

button[data-testid="stExpandSidebarButton"] *,
button[data-testid="stExpandSidebarButton"] span[data-testid="stIconMaterial"] {
    color: white !important;
}

/* Botón collapse sidebar (cuando está abierto) — heredado del sidebar */
button[data-testid="stBaseButton-headerNoPadding"] {
    background-color: #000000 !important;
    border: none !important;
}

/* Toggle de idioma — fondo semitransparente para que no quede blanco sobre azul */
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] [data-testid="stButton"] > button,
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
    border-radius: 10px !important;
    color: white !important;
}

[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: rgba(255,255,255,0.22) !important;
}

/* ==========================================================
   FONDO APP
   ========================================================== */
.stApp {
    background: linear-gradient(
        160deg,
        #050f1c 0%,
        #0b1f3a 50%,
        #071428 100%
    );
}

[data-testid="stMain"],
[data-testid="stAppViewContainer"] {
    background: transparent !important;
}

/* ==========================================================
   SIDEBAR
   ========================================================== */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #001845 0%,
        #003087 40%,
        #3f74c5 100%
    ) !important;

    border-right: 2px solid rgba(255,255,255,.25);
    overflow-x: hidden !important;
}

[data-testid="stSidebarContent"] {
    overflow-x: hidden !important;
}

[data-testid="stSidebar"] * {
    color:white !important;
}

/* ==========================================================
   TÍTULOS DE SECCIÓN (BI / ANÁLISIS)
   data-testid exacto encontrado en el DOM: stNavSectionHeader
   El texto está en el <p> dentro del stMarkdownContainer
   ========================================================== */
[data-testid="stNavSectionHeader"] p {
    font-size: 2.8rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
    color: white !important;
    line-height: 1.1 !important;
    margin: 0 !important;
}

[data-testid="stNavSectionHeader"] {
    margin-top: 20px !important;
    padding: 0 4px 10px 4px !important;
    border-bottom: 1px solid rgba(255,255,255,0.30) !important;
    margin-bottom: 8px !important;
}

/* ==========================================================
   SEPARADOR ENTRE SECCIONES
   El div stSidebarNavSeparator ya existe en el DOM, solo
   hay que darle altura y color visible
   ========================================================== */
[data-testid="stSidebarNavSeparator"] {
    display: none !important;
}

/* ==========================================================
   ITEMS DEL MENÚ
   ========================================================== */
[data-testid="stSidebarNavLink"] {

    font-size: 1.35rem !important;
    font-weight: 700 !important;

    min-height: 60px !important;

    padding: 14px 18px !important;

    border-radius: 12px !important;

    margin-bottom: 4px !important;

    transition: all .2s ease !important;
}

[data-testid="stSidebarNavLink"] span,
[data-testid="stSidebarNavLink"] p {

    font-size: 1.35rem !important;
    font-weight: 700 !important;
}

/* Hover */
[data-testid="stSidebarNavLink"]:hover {

    background: rgba(255,255,255,.10) !important;
}

/* Página seleccionada */
[data-testid="stSidebarNavLink"][aria-current="page"] {

    background: rgba(255,255,255,.18) !important;

    border-radius: 12px !important;
}

/* ==========================================================
   ICONOS
   ========================================================== */
[data-testid="stSidebarNavLink"] svg {
    width: 24px !important;
    height: 24px !important;
}

/* ==========================================================
   MÉTRICAS
   ========================================================== */
[data-testid="metric-container"] {

    border-left: 4px solid #F6B40E;

    background: rgba(255,255,255,.05);

    border-radius: 10px;

    padding-left: 12px;
}

[data-testid="metric-container"] label {
    color:#74ACDF !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color:white !important;
    font-size:2rem;
}

/* ==========================================================
   INPUTS
   ========================================================== */
[data-testid="stSelectbox"] > div > div {

    background: rgba(255,255,255,.08) !important;

    border: 1px solid rgba(255,255,255,.20) !important;

    border-radius: 10px !important;

    color: rgba(255,255,255,0.85) !important;
}

/* React-Select internals: placeholder, valor seleccionado, input */
[data-testid="stSelectbox"] [class*="placeholder"],
[data-testid="stSelectbox"] [class*="singleValue"],
[data-testid="stSelectbox"] [class*="option"],
[data-testid="stSelectbox"] input,
[data-testid="stSelectbox"] p {
    color: rgba(255,255,255,0.85) !important;
}

[data-testid="stSelectbox"] svg {
    fill: rgba(255,255,255,0.7) !important;
    color: rgba(255,255,255,0.7) !important;
}

/* ==========================================================
   TITULOS DEL CONTENIDO
   ========================================================== */
h1,h2,h3 {
    color:#74ACDF !important;
}

/* ==========================================================
   RESPONSIVE — MOBILE (max 768px)
   ========================================================== */
@media (max-width: 768px) {

    /* Columnas se apilan verticalmente */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Sidebar scrolleable en mobile para ver el toggle de idioma */
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {
        overflow-y: auto !important;
    }

    /* Títulos de sección del sidebar más chicos */
    [data-testid="stNavSectionHeader"] p {
        font-size: 1.6rem !important;
    }

    /* Nav links — texto que hace wrap en vez de cortarse */
    [data-testid="stSidebarNavLink"] {
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        padding: 10px 12px !important;
        min-height: 44px !important;
        height: auto !important;
        white-space: normal !important;
    }
    [data-testid="stSidebarNavLink"] span,
    [data-testid="stSidebarNavLink"] p {
        white-space: normal !important;
        word-break: break-word !important;
        overflow: visible !important;
        text-overflow: unset !important;
        font-size: 0.9rem !important;
    }

    /* Títulos de página más chicos */
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }

    /* Métricas más compactas */
    [data-testid="metric-container"] {
        padding: 8px !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }

    /* Iframes de Metabase — altura reducida en mobile */
    iframe[title="st.iframe"] {
        height: 900px !important;
    }

    /* Imagen de pitch — sin márgenes laterales */
    [data-testid="stImage"] img {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* Fix layout="wide" — prevenir scroll horizontal en mobile */
    .block-container {
        max-width: 100vw !important;
        overflow-x: hidden !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }

    /* Footer "Desarrollado por" — ancho responsivo en mobile */
    .dev-footer {
        left: 0 !important;
        right: 0 !important;
        width: auto !important;
        padding: 0 1.5rem !important;
        box-sizing: border-box !important;
    }
}

/* ==========================================================
   RESPONSIVE — MOBILE CHICO (max 480px)
   ========================================================== */
@media (max-width: 480px) {

    /* Títulos más compactos en pantallas muy pequeñas */
    h1 { font-size: 1.3rem !important; line-height: 1.2 !important; }
    h2 { font-size: 1.1rem !important; }

    /* Separadores con menos margen */
    [data-testid="stMarkdownContainer"] hr {
        margin: 0.4rem 0 !important;
    }

    /* Selectboxes — texto y padding reducidos */
    [data-testid="stSelectbox"] > div > div {
        font-size: 0.82rem !important;
        padding: 6px 8px !important;
    }

    /* Métricas — valores y labels más compactos */
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    [data-testid="metric-container"] label {
        font-size: 0.7rem !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.65rem !important;
        white-space: normal !important;
        word-break: break-word !important;
    }

    /* Cajas HTML inline (leyenda heatmap, descripción passmap) */
    [data-testid="stMarkdownContainer"] div[style*="border"] {
        padding: 10px 12px !important;
    }

    /* Filas flex dentro de cajas (stats passmap) — wrap en pantallas muy chicas */
    [data-testid="stMarkdownContainer"] div[style*="display:flex"] {
        flex-wrap: wrap !important;
        gap: 2px !important;
    }
}
</style>
""", unsafe_allow_html=True)

from i18n import render_lang_toggle, get_lang

render_lang_toggle()

_lang = get_lang()

st.sidebar.markdown(
    """
    <div class="dev-footer" style="
        position: fixed;
        bottom: 16px;
        left: 0;
        width: 295px;
        text-align: center;
        font-size: 0.62rem;
        color: rgba(255,255,255,0.45);
        letter-spacing: 0.03em;
        z-index: 999;
    ">
        Desarrollado por<br>
        <a href="https://www.linkedin.com/in/agustin-perez-39b400222/"
           target="_blank"
           style="
               color: rgba(255,255,255,0.80);
               font-size: 0.72rem;
               font-weight: 700;
               text-decoration: none;
               letter-spacing: 0.02em;
           ">
            Agustín Pérez ↗
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)

pg = st.navigation({
    "BI": [
        st.Page("pages/06_Plantel_2024.py", title="Plantel 2024-25" if _lang == "es" else "2024-25 Squad", icon="📊"),
        st.Page("pages/07_Resultados.py",   title="Resultados"       if _lang == "es" else "Results",       icon="📈"),
        st.Page("pages/08_Jugadores_NT.py", title="Jugadores"        if _lang == "es" else "Players",       icon="👤"),
    ],
    ("Análisis" if _lang == "es" else "Analysis"): [
        st.Page("pages/03_Shot_Map.py", title="Mapa de Disparos" if _lang == "es" else "Shot Map", icon="🎯"),
        st.Page("pages/04_Heatmap.py",  title="Mapa de Calor"    if _lang == "es" else "Heat Map", icon="🔥"),
        st.Page("pages/05_Pass_Map.py", title="Mapa de Pases"    if _lang == "es" else "Pass Map", icon="🔵"),
    ],
})
pg.run()
