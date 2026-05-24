# -*- coding: utf-8 -*-
import sys
import os

import matplotlib
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import query

# ---------------------------------------------------------------------------
# Page config & CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Partidos — Scaloneta 2026",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
[data-testid="stSidebar"] { background: #003087; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #74ACDF; }
.stApp { background-color: #0d1117; color: #FFFFFF; }
[data-testid="metric-container"] {
    border-left: 4px solid #F6B40E;
    padding-left: 12px;
    background: #161b22;
    border-radius: 4px;
}
[data-testid="metric-container"] label { color: #74ACDF !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #FFFFFF !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Country flag helper (Unicode regional indicators)
# ---------------------------------------------------------------------------
COUNTRY_FLAGS: dict[str, str] = {
    "Brazil": "🇧🇷", "Uruguay": "🇺🇾", "Colombia": "🇨🇴", "Chile": "🇨🇱",
    "Paraguay": "🇵🇾", "Ecuador": "🇪🇨", "Peru": "🇵🇪", "Bolivia": "🇧🇴",
    "Venezuela": "🇻🇪", "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸",
    "Italy": "🇮🇹", "Netherlands": "🇳🇱", "Portugal": "🇵🇹", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Croatia": "🇭🇷", "Morocco": "🇲🇦", "Mexico": "🇲🇽", "USA": "🇺🇸",
    "Canada": "🇨🇦", "Japan": "🇯🇵", "South Korea": "🇰🇷", "Australia": "🇦🇺",
    "Saudi Arabia": "🇸🇦", "Poland": "🇵🇱", "Denmark": "🇩🇰", "Switzerland": "🇨🇭",
    "Belgium": "🇧🇪", "Serbia": "🇷🇸", "Ghana": "🇬🇭", "Cameroon": "🇨🇲",
    "Senegal": "🇸🇳", "Tunisia": "🇹🇳",
}


def flag(opponent: str) -> str:
    return COUNTRY_FLAGS.get(opponent, "")


# ---------------------------------------------------------------------------
# Cached DB queries
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_matches() -> pd.DataFrame:
    return query("""
        SELECT
            fm.match_id,
            fm.date         AS match_date,
            dc.name         AS competition,
            dc.type         AS competition_type,
            fm.stage,
            fm.opponent,
            fm.result,
            fm.goals_for,
            fm.goals_against,
            fm.xg_for,
            fm.xg_against,
            fm.venue,
            fm.is_neutral
        FROM fact_match fm
        LEFT JOIN dim_competition dc ON fm.competition_id = dc.competition_id
        ORDER BY fm.date DESC
    """)


@st.cache_data(ttl=3600)
def load_competition_stats(comp_filter: list[str]) -> pd.DataFrame:
    """Group stats by competition."""
    df = load_matches()
    if comp_filter:
        df = df[df["competition_type"].isin(comp_filter)]
    if df.empty:
        return pd.DataFrame()
    grp = (
        df.groupby("competition")
        .agg(
            P=("match_id", "count"),
            W=("result", lambda x: (x == "W").sum()),
            D=("result", lambda x: (x == "D").sum()),
            L=("result", lambda x: (x == "L").sum()),
            GF=("goals_for", "sum"),
            GA=("goals_against", "sum"),
            xG_for=("xg_for", "sum"),
            xG_against=("xg_against", "sum"),
        )
        .reset_index()
    )
    grp["GD"] = grp["GF"] - grp["GA"]
    grp["Pts"] = grp["W"] * 3 + grp["D"]
    grp["Win%"] = (grp["W"] / grp["P"] * 100).round(1)
    return grp


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("📅 Filtros — Partidos")

COMPETITION_TYPES = {
    "Mundial (WC)": "WC",
    "Copa América (CA)": "CA",
    "Eliminatorias (WCQ)": "WCQ",
    "Amistosos": "Friendly",
}

selected_comp_labels = st.sidebar.multiselect(
    "Competencia",
    options=list(COMPETITION_TYPES.keys()),
    default=list(COMPETITION_TYPES.keys()),
)
selected_comp_types = [COMPETITION_TYPES[l] for l in selected_comp_labels]

col_d1, col_d2 = st.sidebar.columns(2)
date_from = col_d1.date_input("Desde", value=pd.Timestamp("2022-01-01"))
date_to = col_d2.date_input("Hasta", value=pd.Timestamp("2026-12-31"))

only_wins = st.sidebar.checkbox("Solo victorias", value=False)

# ---------------------------------------------------------------------------
# Load & filter data
# ---------------------------------------------------------------------------
st.title("📅 Partidos — Historial Argentina")

try:
    df_all = load_matches()
except Exception as e:
    st.error(f"No se pudo conectar a la base de datos: {e}")
    st.stop()

if df_all.empty:
    st.warning("No hay datos de partidos en la base de datos. Ejecutá el ETL primero.")
    st.stop()

# Apply filters
df = df_all.copy()
if selected_comp_types:
    df = df[df["competition_type"].isin(selected_comp_types)]

df["match_date"] = pd.to_datetime(df["match_date"])
df = df[
    (df["match_date"] >= pd.Timestamp(date_from))
    & (df["match_date"] <= pd.Timestamp(date_to))
]

if only_wins:
    df = df[df["result"] == "W"]

if df.empty:
    st.warning("No hay partidos que coincidan con los filtros seleccionados.")
    st.stop()

# ---------------------------------------------------------------------------
# Section 1: Summary KPIs
# ---------------------------------------------------------------------------
st.subheader("Resumen")

total = len(df)
wins = (df["result"] == "W").sum()
draws = (df["result"] == "D").sum()
losses = (df["result"] == "L").sum()
win_pct = wins / total * 100 if total > 0 else 0
gf = df["goals_for"].sum()
ga = df["goals_against"].sum()
xg_for = df["xg_for"].sum() if "xg_for" in df.columns else 0
xg_against = df["xg_against"].sum() if "xg_against" in df.columns else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Partidos", total)
k2.metric("Win%", f"{win_pct:.1f}%", f"{wins}V {draws}E {losses}D")
k3.metric("Goles a favor", int(gf), f"xG {xg_for:.1f}" if xg_for else None)
k4.metric("Goles en contra", int(ga), f"xGA {xg_against:.1f}" if xg_against else None)
k5.metric("GD", f"{int(gf - ga):+d}")
k6.metric("Racha actual", _current_streak(df))

st.markdown("---")


def _current_streak(df: pd.DataFrame) -> str:
    """Return e.g. '5W' or '3D' describing the current unbeaten/form streak."""
    if df.empty:
        return "—"
    sorted_df = df.sort_values("match_date", ascending=False)
    results = sorted_df["result"].tolist()
    if not results:
        return "—"
    streak_char = results[0]
    count = 0
    for r in results:
        if r == streak_char:
            count += 1
        else:
            break
    label_map = {"W": "V", "D": "E", "L": "D"}
    return f"{count}{label_map.get(streak_char, streak_char)}"


# ---------------------------------------------------------------------------
# Section 2: Resultados recientes
# ---------------------------------------------------------------------------
st.subheader("Resultados recientes (últimos 10)")

df_recent = df.sort_values("match_date", ascending=False).head(10).copy()
df_recent["Rival"] = df_recent["opponent"].apply(
    lambda o: f"{flag(o)} {o}" if flag(o) else o
)
df_recent["Marcador"] = df_recent.apply(
    lambda r: f"{int(r['goals_for'])}–{int(r['goals_against'])}", axis=1
)
df_recent["xG"] = df_recent["xg_for"].apply(
    lambda v: f"{v:.2f}" if pd.notna(v) else "—"
)
df_recent["xGA"] = df_recent["xg_against"].apply(
    lambda v: f"{v:.2f}" if pd.notna(v) else "—"
)

display_cols = {
    "match_date": "Fecha",
    "competition": "Competencia",
    "stage": "Instancia",
    "Rival": "Rival",
    "result": "Resultado",
    "Marcador": "Marcador",
    "xG": "xG",
    "xGA": "xGA",
}
df_display = df_recent[list(display_cols.keys())].rename(columns=display_cols)
df_display["Fecha"] = df_display["Fecha"].dt.strftime("%d/%m/%Y")

st.dataframe(
    df_display,
    column_config={
        "Resultado": st.column_config.TextColumn(
            "Resultado",
            help="W=Victoria, D=Empate, L=Derrota",
        ),
        "Fecha": st.column_config.TextColumn("Fecha"),
    },
    hide_index=True,
    use_container_width=True,
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Section 3: Estadísticas por competencia
# ---------------------------------------------------------------------------
st.subheader("Estadísticas por competencia")

try:
    df_comp = load_competition_stats(selected_comp_types)
    if not df_comp.empty:
        # Grouped bar chart
        fig_comp = go.Figure()
        metrics = ["W", "D", "L", "GF", "GA"]
        colors_bar = ["#74ACDF", "#AAAAAA", "#E05050", "#F6B40E", "#FF9999"]
        for metric, color in zip(metrics, colors_bar):
            fig_comp.add_trace(
                go.Bar(
                    name=metric,
                    x=df_comp["competition"],
                    y=df_comp[metric],
                    marker_color=color,
                )
            )
        fig_comp.update_layout(
            barmode="group",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font_color="white",
            legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
            xaxis=dict(gridcolor="#2a2a3e"),
            yaxis=dict(gridcolor="#2a2a3e"),
            title=dict(text="Partidos por competencia", font=dict(color="#74ACDF")),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Summary table
        table_cols = ["competition", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "Win%"]
        available = [c for c in table_cols if c in df_comp.columns]
        st.dataframe(
            df_comp[available].rename(columns={"competition": "Competencia"}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Sin datos de competencias para los filtros seleccionados.")
except Exception as e:
    st.warning(f"No se pudieron cargar las estadísticas por competencia: {e}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Section 4: Forma reciente
# ---------------------------------------------------------------------------
st.subheader("Forma reciente")

df_form = df.sort_values("match_date").copy()
df_form["xg_for"] = pd.to_numeric(df_form["xg_for"], errors="coerce").fillna(0)
df_form["xg_against"] = pd.to_numeric(df_form["xg_against"], errors="coerce").fillna(0)
df_form["goals_for"] = pd.to_numeric(df_form["goals_for"], errors="coerce").fillna(0)
df_form["goals_against"] = pd.to_numeric(df_form["goals_against"], errors="coerce").fillna(0)

WINDOW = 5
df_form["xG_roll"] = df_form["xg_for"].rolling(WINDOW, min_periods=1).mean()
df_form["xGA_roll"] = df_form["xg_against"].rolling(WINDOW, min_periods=1).mean()
df_form["GF_roll"] = df_form["goals_for"].rolling(WINDOW, min_periods=1).mean()
df_form["GA_roll"] = df_form["goals_against"].rolling(WINDOW, min_periods=1).mean()
df_form["match_label"] = df_form["match_date"].dt.strftime("%d/%m/%y") + " " + df_form["opponent"].fillna("")

col_form1, col_form2 = st.columns(2)

with col_form1:
    fig_xg = go.Figure()
    fig_xg.add_trace(
        go.Scatter(
            x=df_form["match_label"],
            y=df_form["xG_roll"],
            mode="lines+markers",
            name="xG favor (rolling 5)",
            line=dict(color="#74ACDF", width=2),
            marker=dict(size=6),
        )
    )
    fig_xg.add_trace(
        go.Scatter(
            x=df_form["match_label"],
            y=df_form["xGA_roll"],
            mode="lines+markers",
            name="xGA en contra (rolling 5)",
            line=dict(color="#F6B40E", width=2, dash="dot"),
            marker=dict(size=6),
        )
    )
    fig_xg.update_layout(
        title=dict(text=f"xG media móvil ({WINDOW} partidos)", font=dict(color="#74ACDF")),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font_color="white",
        xaxis=dict(gridcolor="#2a2a3e", tickangle=-45),
        yaxis=dict(gridcolor="#2a2a3e"),
        legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
    )
    st.plotly_chart(fig_xg, use_container_width=True)

with col_form2:
    result_color_map = {"W": "#74ACDF", "D": "#AAAAAA", "L": "#E05050"}
    df_form["color"] = df_form["result"].map(result_color_map).fillna("#888888")
    fig_scatter = go.Figure()
    for res, label, color in [("W", "Victoria", "#74ACDF"), ("D", "Empate", "#AAAAAA"), ("L", "Derrota", "#E05050")]:
        mask = df_form["result"] == res
        fig_scatter.add_trace(
            go.Scatter(
                x=df_form.loc[mask, "match_label"],
                y=df_form.loc[mask, "goals_for"],
                mode="markers",
                name=label,
                marker=dict(color=color, size=10, symbol="circle"),
                text=df_form.loc[mask, "opponent"],
                hovertemplate="<b>%{text}</b><br>Goles: %{y}<extra></extra>",
            )
        )
    fig_scatter.update_layout(
        title=dict(text="Goles marcados por partido", font=dict(color="#74ACDF")),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font_color="white",
        xaxis=dict(gridcolor="#2a2a3e", tickangle=-45),
        yaxis=dict(gridcolor="#2a2a3e", title="Goles"),
        legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
