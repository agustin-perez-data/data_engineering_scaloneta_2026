import sys
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# DejaVu Sans soporta el alfabeto latino completo: ñ, á, é, í, ó, ú, ü, etc.
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import query

# ---------------------------------------------------------------------------
# Page config & CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Jugadores — Scaloneta 2026",
    page_icon="👤",
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
# Theme colors
# ---------------------------------------------------------------------------
COLORS = ["#74ACDF", "#F6B40E", "#FFFFFF", "#FF6B6B"]
POSITION_COLORS = {"GK": "#74ACDF", "DF": "#4CAF50", "MF": "#F6B40E", "FW": "#E05050"}

# ---------------------------------------------------------------------------
# Cached DB queries
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_players() -> pd.DataFrame:
    return query("""
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            p.current_club  AS club,
            p.current_league AS league
        FROM dim_player p
        ORDER BY p.position, p.player_name
    """)


@st.cache_data(ttl=3600)
def load_player_national_stats() -> pd.DataFrame:
    """Aggregate stats per player from national team matches."""
    return query("""
        SELECT
            fpm.player_id,
            p.player_name,
            p.position,
            p.current_club        AS club,
            dc.name               AS competition,
            dc.type               AS competition_type,
            SUM(fpm.minutes_played)           AS minutes,
            SUM(fpm.goals)                    AS goals,
            SUM(fpm.assists)                  AS assists,
            SUM(fpm.xg)                       AS xg,
            SUM(fpm.xag)                      AS xag,
            SUM(fpm.shots)                    AS shots,
            SUM(fpm.shots_on_target)          AS shots_on_target,
            SUM(fpm.passes_attempted)         AS passes,
            SUM(fpm.passes_completed)         AS passes_completed,
            SUM(fpm.key_passes)               AS key_passes,
            SUM(fpm.progressive_passes)       AS progressive_passes,
            SUM(fpm.tackles)                  AS tackles,
            SUM(fpm.interceptions)            AS interceptions,
            SUM(fpm.saves)                    AS saves,
            SUM(CASE WHEN fpm.clean_sheet THEN 1 ELSE 0 END) AS clean_sheets,
            SUM(fpm.psxg)                     AS psxg_ga,
            COUNT(fpm.match_id)               AS appearances
        FROM fact_player_match fpm
        JOIN dim_player p ON fpm.player_id = p.player_id
        LEFT JOIN fact_match fm ON fpm.match_id = fm.match_id
        LEFT JOIN dim_competition dc ON fm.competition_id = dc.competition_id
        GROUP BY fpm.player_id, p.player_name, p.position, p.current_club,
                 dc.name, dc.type
    """)


@st.cache_data(ttl=3600)
def load_player_club_stats() -> pd.DataFrame:
    """Season stats from clubs."""
    return query("""
        SELECT
            fpcs.player_id,
            p.player_name,
            p.position,
            fpcs.season,
            fpcs.club,
            fpcs.league,
            fpcs.matches_played  AS matches,
            fpcs.minutes,
            fpcs.goals,
            fpcs.assists,
            fpcs.xg,
            fpcs.xag,
            fpcs.shots,
            fpcs.shots_on_target,
            fpcs.pass_pct,
            fpcs.progressive_passes,
            fpcs.tackles,
            fpcs.interceptions,
            fpcs.saves,
            fpcs.clean_sheets
        FROM fact_player_club_season fpcs
        JOIN dim_player p ON fpcs.player_id = p.player_id
        ORDER BY fpcs.season DESC
    """)


@st.cache_data(ttl=3600)
def load_player_events(player_id: int) -> pd.DataFrame:
    """Fetch x/y positions from StatsBomb events for heatmap."""
    return query(
        """
        SELECT x, y
        FROM event_statsbomb
        WHERE player_id = :pid
          AND x IS NOT NULL
          AND y IS NOT NULL
        """,
        {"pid": player_id},
    )


@st.cache_data(ttl=3600)
def load_cumulative_stats(player_ids: list[int]) -> pd.DataFrame:
    """Match-by-match stats for cumulative evolution chart."""
    if not player_ids:
        return pd.DataFrame()
    ids_str = ",".join(str(i) for i in player_ids)
    return query(f"""
        SELECT
            fpm.player_id,
            p.player_name,
            fm.date             AS match_date,
            dc.name             AS competition,
            fpm.goals,
            fpm.assists,
            fpm.xg,
            fpm.minutes_played  AS minutes
        FROM fact_player_match fpm
        JOIN dim_player p ON fpm.player_id = p.player_id
        JOIN fact_match fm ON fpm.match_id = fm.match_id
        LEFT JOIN dim_competition dc ON fm.competition_id = dc.competition_id
        WHERE fpm.player_id IN ({ids_str})
        ORDER BY fpm.player_id, fm.date
    """)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if pd.notna(val) else default
    except (TypeError, ValueError):
        return default


def normalize_stats(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Normalize each column 0-100 relative to its max across the dataframe."""
    out = df.copy()
    for col in cols:
        if col in out.columns:
            col_max = out[col].max()
            if col_max and col_max > 0:
                out[col] = (out[col] / col_max * 100).round(1)
            else:
                out[col] = 0.0
    return out


def radar_chart(players_data: dict, categories: list, title: str) -> plt.Figure:
    """Draw a polar radar chart for up to 4 players."""
    N = len(categories)
    if N == 0:
        fig, ax = plt.subplots(figsize=(8, 8))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes,
                ha="center", va="center", color="white", fontsize=14)
        return fig

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.spines["polar"].set_color("#74ACDF")
    ax.tick_params(colors="white")
    ax.yaxis.set_tick_params(labelcolor="white")
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#888888", size=7)
    ax.grid(color="#2a2a3e", linewidth=0.5)

    for i, (player_name, values) in enumerate(players_data.items()):
        vals = list(values) + [values[0]]
        color = COLORS[i % len(COLORS)]
        ax.plot(angles, vals, "o-", linewidth=2, color=color, label=player_name)
        ax.fill(angles, vals, alpha=0.15, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color="white", size=9)
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.35, 1.15),
        labelcolor="white",
        facecolor="#1a1a2e",
        edgecolor="#74ACDF",
        fontsize=9,
    )
    ax.set_title(title, color="#74ACDF", size=13, pad=20)
    return fig


def plot_player_heatmap(player_id: int, player_name: str) -> plt.Figure:
    """Render a KDE heatmap on a StatsBomb pitch for a single player."""
    try:
        from mplsoccer import Pitch
    except ImportError:
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        ax.text(0.5, 0.5, "mplsoccer no disponible", ha="center", va="center",
                color="white", fontsize=12, transform=ax.transAxes)
        return fig

    df_ev = load_player_events(player_id)

    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a472a",
        line_color="white",
        line_zorder=2,
        corner_arcs=True,
    )
    fig, ax = pitch.draw(figsize=(12, 8))
    fig.patch.set_facecolor("#0d1117")

    if len(df_ev) < 10:
        ax.text(
            60, 40,
            "Sin datos de eventos disponibles\npara esta competencia",
            ha="center", va="center",
            color="white", fontsize=14,
        )
        ax.set_title(f"{player_name} — Mapa de calor", color="white", fontsize=14, pad=10)
        return fig

    pitch.kdeplot(
        df_ev["x"].values,
        df_ev["y"].values,
        ax=ax,
        cmap="YlOrRd",
        fill=True,
        levels=100,
        alpha=0.75,
        zorder=1,
    )
    ax.set_title(
        f"{player_name} — Mapa de calor de posicionamiento",
        color="white", fontsize=14, pad=10,
    )
    return fig


# ---------------------------------------------------------------------------
# Load base data
# ---------------------------------------------------------------------------
st.title("👤 Jugadores — Análisis y Comparación")

try:
    df_players = load_players()
except Exception as e:
    st.error(f"No se pudo conectar a la base de datos: {e}")
    st.stop()

if df_players.empty:
    st.warning("No hay datos de jugadores. Ejecutá el ETL primero.")
    st.stop()

try:
    df_national = load_player_national_stats()
except Exception as e:
    st.warning(f"No se pudieron cargar las estadísticas nacionales: {e}")
    df_national = pd.DataFrame()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.title("👤 Controles — Jugadores")

# Position filter
position_filter = st.sidebar.radio(
    "Filtrar por posición",
    options=["Todos", "GK", "DF", "MF", "FW"],
    index=0,
    horizontal=True,
)

# Apply position filter to player list
if position_filter == "Todos":
    filtered_players = df_players
else:
    filtered_players = df_players[df_players["position"] == position_filter]

player_names = filtered_players["player_name"].sort_values().tolist()

# Default players: Messi + Lautaro (fall back gracefully)
defaults = []
for pref in ["Lionel Messi", "Lautaro Martínez", "Lautaro Martinez"]:
    if pref in player_names:
        defaults.append(pref)
        break
for pref in ["Lautaro Martínez", "Lautaro Martinez", "Julián Álvarez", "Julian Alvarez"]:
    if pref in player_names and pref not in defaults:
        defaults.append(pref)
        break
if not defaults and player_names:
    defaults = player_names[:2]

selected_names = st.sidebar.multiselect(
    "Jugadores a comparar (máx. 4)",
    options=player_names,
    default=defaults[:4],
    max_selections=4,
)

# Stats toggle
stats_source = st.sidebar.radio(
    "Ver estadísticas de",
    options=["Selección", "Club"],
    index=0,
)

# Competition filter for national stats
comp_options_sidebar = ["Todos"] + (
    sorted(df_national["competition"].dropna().unique().tolist())
    if not df_national.empty and "competition" in df_national.columns
    else []
)
selected_comp_sidebar = st.sidebar.selectbox("Competencia (selección)", comp_options_sidebar)

# ---------------------------------------------------------------------------
# Resolve selected player IDs and rows
# ---------------------------------------------------------------------------
selected_player_rows = df_players[df_players["player_name"].isin(selected_names)]
selected_ids = selected_player_rows["player_id"].tolist()

if not selected_names:
    st.info("Seleccioná al menos un jugador en el panel lateral para ver la comparación.")
    st.stop()

# ---------------------------------------------------------------------------
# Aggregate national stats for selected players
# ---------------------------------------------------------------------------
def get_aggregated_national(player_ids: list, comp_filter: str) -> pd.DataFrame:
    if df_national.empty:
        return pd.DataFrame()
    df = df_national[df_national["player_id"].isin(player_ids)].copy()
    if comp_filter != "Todos" and "competition" in df.columns:
        df = df[df["competition"] == comp_filter]
    if df.empty:
        return pd.DataFrame()
    numeric_cols = [
        "minutes", "goals", "assists", "xg", "xag", "shots", "shots_on_target",
        "passes", "passes_completed", "key_passes", "progressive_passes",
        "tackles", "interceptions", "saves", "saves_faced", "clean_sheets",
        "psxg_ga", "appearances",
    ]
    agg_dict = {c: "sum" for c in numeric_cols if c in df.columns}
    grouped = (
        df.groupby(["player_id", "player_name", "position", "club"])
        .agg(agg_dict)
        .reset_index()
    )
    return grouped


df_agg = get_aggregated_national(selected_ids, selected_comp_sidebar)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Comparación", "🔥 Heatmap", "📈 Evolución", "⚽ xG vs Goles", "📋 Tabla"]
)

# ============================================================
# TAB 1 — Radar Chart
# ============================================================
with tab1:
    st.subheader("Comparación por radar")

    if df_agg.empty:
        st.warning("No hay estadísticas disponibles para los jugadores/competencia seleccionados.")
    else:
        # Determine categories based on position of majority of selected players
        positions_selected = (
            df_players[df_players["player_id"].isin(selected_ids)]["position"]
            .mode()
            .values
        )
        is_gk = len(positions_selected) > 0 and positions_selected[0] == "GK"

        if is_gk:
            CATEGORIES = [
                "Saves", "Save%", "Clean sheets", "PSxG-GA",
                "Minutes", "Appearances",
            ]
            STAT_COLS = [
                "saves", "save_pct", "clean_sheets", "psxg_ga",
                "minutes", "appearances",
            ]
        else:
            CATEGORIES = [
                "Goals", "Assists", "xG", "Shots on target%",
                "Pass%", "Prog. passes", "Tackles+Int.", "Key passes",
            ]
            STAT_COLS = [
                "goals", "assists", "xg", "shot_on_target_pct",
                "pass_pct", "progressive_passes", "tackles_interceptions",
                "key_passes",
            ]

        # Compute derived stats
        df_radar = df_agg.copy()
        if "shots" in df_radar.columns and "shots_on_target" in df_radar.columns:
            df_radar["shot_on_target_pct"] = np.where(
                df_radar["shots"] > 0,
                df_radar["shots_on_target"] / df_radar["shots"] * 100,
                0,
            )
        else:
            df_radar["shot_on_target_pct"] = 0

        if "passes_completed" in df_radar.columns and "passes" in df_radar.columns:
            df_radar["pass_pct"] = np.where(
                df_radar["passes"] > 0,
                df_radar["passes_completed"] / df_radar["passes"] * 100,
                0,
            )
        else:
            df_radar["pass_pct"] = 0

        if "tackles" in df_radar.columns and "interceptions" in df_radar.columns:
            df_radar["tackles_interceptions"] = df_radar["tackles"].fillna(0) + df_radar["interceptions"].fillna(0)
        else:
            df_radar["tackles_interceptions"] = 0

        if "saves" in df_radar.columns and "saves_faced" in df_radar.columns:
            df_radar["save_pct"] = np.where(
                df_radar["saves_faced"] > 0,
                df_radar["saves"] / df_radar["saves_faced"] * 100,
                0,
            )
        else:
            df_radar["save_pct"] = 0

        # Add missing columns as zeros
        for col in STAT_COLS:
            if col not in df_radar.columns:
                df_radar[col] = 0

        # Normalize using max from ALL players in squad (not just selected)
        df_all_players_agg = get_aggregated_national(
            df_players["player_id"].tolist(), selected_comp_sidebar
        )
        if df_all_players_agg.empty:
            df_norm_ref = df_radar
        else:
            df_norm_ref = df_all_players_agg.copy()
            if "shots" in df_norm_ref.columns and "shots_on_target" in df_norm_ref.columns:
                df_norm_ref["shot_on_target_pct"] = np.where(
                    df_norm_ref["shots"] > 0,
                    df_norm_ref["shots_on_target"] / df_norm_ref["shots"] * 100, 0)
            else:
                df_norm_ref["shot_on_target_pct"] = 0
            if "passes_completed" in df_norm_ref.columns and "passes" in df_norm_ref.columns:
                df_norm_ref["pass_pct"] = np.where(
                    df_norm_ref["passes"] > 0,
                    df_norm_ref["passes_completed"] / df_norm_ref["passes"] * 100, 0)
            else:
                df_norm_ref["pass_pct"] = 0
            if "tackles" in df_norm_ref.columns and "interceptions" in df_norm_ref.columns:
                df_norm_ref["tackles_interceptions"] = df_norm_ref["tackles"].fillna(0) + df_norm_ref["interceptions"].fillna(0)
            else:
                df_norm_ref["tackles_interceptions"] = 0
            if "saves" in df_norm_ref.columns and "saves_faced" in df_norm_ref.columns:
                df_norm_ref["save_pct"] = np.where(
                    df_norm_ref["saves_faced"] > 0,
                    df_norm_ref["saves"] / df_norm_ref["saves_faced"] * 100, 0)
            else:
                df_norm_ref["save_pct"] = 0
            for col in STAT_COLS:
                if col not in df_norm_ref.columns:
                    df_norm_ref[col] = 0

        # Build players_data dict with normalized values
        players_data = {}
        for _, row in df_radar.iterrows():
            name = row["player_name"]
            vals = []
            for col in STAT_COLS:
                raw = safe_float(row.get(col, 0))
                col_max = safe_float(df_norm_ref[col].max(), default=1) if col in df_norm_ref.columns else 1
                normalized = (raw / col_max * 100) if col_max > 0 else 0
                vals.append(min(round(normalized, 1), 100))
            players_data[name] = vals

        col_radar, col_table = st.columns([3, 2])

        with col_radar:
            fig_radar = radar_chart(players_data, CATEGORIES, "Comparación de jugadores")
            st.pyplot(fig_radar, use_container_width=True)
            plt.close(fig_radar)

        with col_table:
            st.markdown("**Estadísticas brutas**")
            display_stat_cols = [c for c in STAT_COLS if c in df_radar.columns]
            stat_table = df_radar[["player_name", "position"] + display_stat_cols].copy()
            stat_table = stat_table.rename(columns={
                "player_name": "Jugador", "position": "Pos",
                "goals": "G", "assists": "A", "xg": "xG", "xag": "xAG",
                "shots": "Tiros", "shots_on_target": "Tiros SOT",
                "shot_on_target_pct": "SOT%", "passes": "Pases",
                "passes_completed": "Pases OK", "pass_pct": "Pase%",
                "progressive_passes": "Prog P", "key_passes": "K Pases",
                "tackles": "Tacles", "interceptions": "Int",
                "tackles_interceptions": "Tac+Int",
                "saves": "Atajadas", "save_pct": "Ataj%",
                "clean_sheets": "Valla 0", "psxg_ga": "PSxG-GA",
                "minutes": "Min", "appearances": "PJ",
            })
            # Round all numeric columns
            num_cols = stat_table.select_dtypes(include="number").columns
            stat_table[num_cols] = stat_table[num_cols].round(2)
            st.dataframe(stat_table, hide_index=True, use_container_width=True)

# ============================================================
# TAB 2 — Heatmap
# ============================================================
with tab2:
    st.subheader("Mapa de calor de posicionamiento")
    st.info(
        "Datos de eventos StatsBomb disponibles para: Qatar 2022, Copa América 2021. "
        "Se muestran todas las acciones registradas del jugador en esas competencias."
    )

    if not selected_names:
        st.warning("Seleccioná jugadores en el panel lateral.")
    else:
        # Show 2 per row
        for i in range(0, len(selected_names), 2):
            cols_hm = st.columns(2)
            for j, col_hm in enumerate(cols_hm):
                idx = i + j
                if idx >= len(selected_names):
                    break
                pname = selected_names[idx]
                pid_rows = df_players[df_players["player_name"] == pname]
                if pid_rows.empty:
                    col_hm.warning(f"Jugador no encontrado: {pname}")
                    continue
                pid = int(pid_rows.iloc[0]["player_id"])
                with col_hm:
                    with st.spinner(f"Cargando heatmap de {pname}..."):
                        try:
                            fig_hm = plot_player_heatmap(pid, pname)
                            st.pyplot(fig_hm, use_container_width=True)
                            plt.close(fig_hm)
                        except Exception as e:
                            st.warning(f"No se pudo generar el heatmap de {pname}: {e}")

# ============================================================
# TAB 3 — Evolución temporal
# ============================================================
with tab3:
    st.subheader("Evolución temporal")

    if not selected_ids:
        st.warning("Seleccioná jugadores en el panel lateral.")
    else:
        try:
            with st.spinner("Cargando datos de evolución..."):
                df_cum = load_cumulative_stats(selected_ids)
        except Exception as e:
            st.warning(f"No se pudo cargar la evolución: {e}")
            df_cum = pd.DataFrame()

        if df_cum.empty:
            st.info("Sin datos de evolución para los jugadores seleccionados.")
        else:
            df_cum["match_date"] = pd.to_datetime(df_cum["match_date"])
            df_cum = df_cum.sort_values(["player_name", "match_date"])

            # Cumulative goals + assists
            df_cum["goals"] = pd.to_numeric(df_cum["goals"], errors="coerce").fillna(0)
            df_cum["assists"] = pd.to_numeric(df_cum["assists"], errors="coerce").fillna(0)
            df_cum["G+A"] = df_cum["goals"] + df_cum["assists"]
            df_cum["cum_goals"] = df_cum.groupby("player_name")["goals"].cumsum()
            df_cum["cum_assists"] = df_cum.groupby("player_name")["assists"].cumsum()
            df_cum["cum_ga"] = df_cum.groupby("player_name")["G+A"].cumsum()

            col_ev1, col_ev2 = st.columns(2)

            with col_ev1:
                fig_cum_goals = px.line(
                    df_cum,
                    x="match_date",
                    y="cum_goals",
                    color="player_name",
                    title="Goles acumulados en selección",
                    labels={"match_date": "Fecha", "cum_goals": "Goles", "player_name": "Jugador"},
                    color_discrete_sequence=COLORS,
                )
                fig_cum_goals.update_layout(
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0d1117",
                    font_color="white",
                    xaxis=dict(gridcolor="#2a2a3e"),
                    yaxis=dict(gridcolor="#2a2a3e"),
                    legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
                    title=dict(font=dict(color="#74ACDF")),
                )
                st.plotly_chart(fig_cum_goals, use_container_width=True)

            with col_ev2:
                fig_cum_ga = px.line(
                    df_cum,
                    x="match_date",
                    y="cum_ga",
                    color="player_name",
                    title="G+A acumulados en selección",
                    labels={"match_date": "Fecha", "cum_ga": "G+A", "player_name": "Jugador"},
                    color_discrete_sequence=COLORS,
                )
                fig_cum_ga.update_layout(
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0d1117",
                    font_color="white",
                    xaxis=dict(gridcolor="#2a2a3e"),
                    yaxis=dict(gridcolor="#2a2a3e"),
                    legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
                    title=dict(font=dict(color="#74ACDF")),
                )
                st.plotly_chart(fig_cum_ga, use_container_width=True)

            # Goals/assists per competition (stacked bar)
            if "competition" in df_cum.columns:
                df_by_comp = (
                    df_cum.groupby(["player_name", "competition"])
                    .agg(goals=("goals", "sum"), assists=("assists", "sum"))
                    .reset_index()
                )
                fig_bar_comp = go.Figure()
                for pname in df_by_comp["player_name"].unique():
                    pdata = df_by_comp[df_by_comp["player_name"] == pname]
                    fig_bar_comp.add_trace(
                        go.Bar(
                            name=f"{pname} — Goles",
                            x=pdata["competition"],
                            y=pdata["goals"],
                            text=pdata["goals"],
                            textposition="inside",
                        )
                    )
                fig_bar_comp.update_layout(
                    barmode="group",
                    title=dict(text="Goles por competencia", font=dict(color="#74ACDF")),
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0d1117",
                    font_color="white",
                    xaxis=dict(gridcolor="#2a2a3e"),
                    yaxis=dict(gridcolor="#2a2a3e"),
                    legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
                )
                st.plotly_chart(fig_bar_comp, use_container_width=True)

# ============================================================
# TAB 4 — xG vs Goles
# ============================================================
with tab4:
    st.subheader("xG vs Goles reales")

    if df_national.empty:
        st.warning("No hay datos de estadísticas nacionales disponibles.")
    else:
        # Aggregate all players
        try:
            df_all_agg = get_aggregated_national(
                df_players["player_id"].tolist(), selected_comp_sidebar
            )
        except Exception as e:
            st.warning(f"No se pudieron cargar los datos: {e}")
            df_all_agg = pd.DataFrame()

        if df_all_agg.empty:
            st.info("Sin datos para el filtro de competencia seleccionado.")
        else:
            df_xg = df_all_agg.copy()
            df_xg["xg"] = pd.to_numeric(df_xg.get("xg", 0), errors="coerce").fillna(0)
            df_xg["goals"] = pd.to_numeric(df_xg.get("goals", 0), errors="coerce").fillna(0)
            df_xg["minutes"] = pd.to_numeric(df_xg.get("minutes", 0), errors="coerce").fillna(0)
            df_xg["xg_diff"] = df_xg["goals"] - df_xg["xg"]
            df_xg["position"] = df_xg.get("position", "MF")

            # Labels for key players
            KEY_PLAYERS = {"Lionel Messi", "Lautaro Martínez", "Lautaro Martinez",
                           "Julián Álvarez", "Julian Alvarez"}

            fig_xg_scatter = go.Figure()

            # Diagonal calibration line
            max_val = max(
                df_xg["xg"].max() if not df_xg.empty else 1,
                df_xg["goals"].max() if not df_xg.empty else 1,
            ) * 1.1
            fig_xg_scatter.add_trace(
                go.Scatter(
                    x=[0, max_val], y=[0, max_val],
                    mode="lines",
                    name="xG = Goles",
                    line=dict(color="#888888", dash="dash", width=1),
                    showlegend=True,
                )
            )

            for pos, pos_color in POSITION_COLORS.items():
                mask = df_xg["position"] == pos
                subset = df_xg[mask]
                if subset.empty:
                    continue
                fig_xg_scatter.add_trace(
                    go.Scatter(
                        x=subset["xg"],
                        y=subset["goals"],
                        mode="markers",
                        name=pos,
                        marker=dict(
                            color=pos_color,
                            size=np.clip(subset["minutes"] / 50, 8, 30).fillna(8).tolist(),
                            opacity=0.8,
                            line=dict(color="white", width=1),
                        ),
                        customdata=np.stack([
                            subset["player_name"],
                            subset["goals"],
                            subset["xg"].round(2),
                            subset["xg_diff"].round(2),
                            subset["minutes"].astype(int),
                        ], axis=-1),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Goles: %{customdata[1]}<br>"
                            "xG: %{customdata[2]}<br>"
                            "Diferencia: %{customdata[3]:+.2f}<br>"
                            "Minutos: %{customdata[4]}<extra></extra>"
                        ),
                    )
                )

            # Annotations for key players
            for _, row in df_xg[df_xg["player_name"].isin(KEY_PLAYERS)].iterrows():
                fig_xg_scatter.add_annotation(
                    x=row["xg"],
                    y=row["goals"],
                    text=row["player_name"].split()[-1],
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#F6B40E",
                    font=dict(color="#F6B40E", size=10),
                    bgcolor="#0d1117",
                    bordercolor="#F6B40E",
                    ax=15,
                    ay=-25,
                )

            fig_xg_scatter.update_layout(
                title=dict(
                    text="xG vs Goles reales — Eficiencia de definición",
                    font=dict(color="#74ACDF"),
                ),
                xaxis=dict(title="xG total", gridcolor="#2a2a3e", zeroline=False),
                yaxis=dict(title="Goles reales", gridcolor="#2a2a3e", zeroline=False),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font_color="white",
                legend=dict(bgcolor="#161b22", bordercolor="#74ACDF"),
            )

            st.plotly_chart(fig_xg_scatter, use_container_width=True)

            st.caption(
                "Puntos sobre la diagonal = mejor rendimiento que el xG (finalizadores eficientes). "
                "Tamaño del punto proporcional a los minutos jugados."
            )

            # Top over/under performers table
            col_over, col_under = st.columns(2)
            df_xg_sorted = df_xg[df_xg["minutes"] > 0].sort_values("xg_diff", ascending=False)
            with col_over:
                st.markdown("**Top finalizadores (sobre-rendimiento)**")
                top_over = df_xg_sorted.head(5)[["player_name", "goals", "xg", "xg_diff", "position"]]
                top_over = top_over.rename(columns={
                    "player_name": "Jugador", "goals": "G", "xg": "xG",
                    "xg_diff": "G-xG", "position": "Pos"
                })
                top_over["xG"] = top_over["xG"].round(2)
                top_over["G-xG"] = top_over["G-xG"].round(2)
                st.dataframe(top_over, hide_index=True, use_container_width=True)
            with col_under:
                st.markdown("**Jugadores bajo xG**")
                top_under = df_xg_sorted.tail(5)[["player_name", "goals", "xg", "xg_diff", "position"]]
                top_under = top_under.rename(columns={
                    "player_name": "Jugador", "goals": "G", "xg": "xG",
                    "xg_diff": "G-xG", "position": "Pos"
                })
                top_under["xG"] = top_under["xG"].round(2)
                top_under["G-xG"] = top_under["G-xG"].round(2)
                st.dataframe(top_under, hide_index=True, use_container_width=True)

# ============================================================
# TAB 5 — Tabla completa
# ============================================================
with tab5:
    st.subheader("Tabla completa de jugadores")

    # Toggle: selección / club
    if stats_source == "Selección":
        if df_national.empty:
            st.warning("No hay datos de selección disponibles.")
        else:
            # Competition filter
            comp_opts_tab5 = ["Todos"] + sorted(
                df_national["competition"].dropna().unique().tolist()
            )
            comp_tab5 = st.selectbox("Filtrar competencia", comp_opts_tab5, key="tab5_comp")

            df_tab5 = df_national.copy()
            if comp_tab5 != "Todos":
                df_tab5 = df_tab5[df_tab5["competition"] == comp_tab5]

            if position_filter != "Todos":
                df_tab5 = df_tab5[df_tab5["position"] == position_filter]

            # Aggregate
            numeric_agg = [
                c for c in [
                    "minutes", "goals", "assists", "xg", "xag", "shots",
                    "shots_on_target", "passes", "passes_completed", "key_passes",
                    "progressive_passes", "tackles", "interceptions",
                    "saves", "saves_faced", "clean_sheets", "psxg_ga", "appearances",
                ]
                if c in df_tab5.columns
            ]
            df_tab5_agg = (
                df_tab5.groupby(["player_id", "player_name", "position", "club"])
                .agg({c: "sum" for c in numeric_agg})
                .reset_index()
                .sort_values("goals", ascending=False)
            )

            # Rename for display
            rename_map = {
                "player_name": "Jugador", "position": "Pos", "club": "Club",
                "appearances": "PJ", "minutes": "Min", "goals": "G", "assists": "A",
                "xg": "xG", "xag": "xAG", "shots": "Tiros",
                "shots_on_target": "SOT", "passes": "Pases",
                "passes_completed": "Pases OK", "key_passes": "K Pases",
                "progressive_passes": "Prog P", "tackles": "Tacles",
                "interceptions": "Int", "saves": "Atajadas",
                "saves_faced": "Ataj Faced", "clean_sheets": "Valla 0",
                "psxg_ga": "PSxG-GA",
            }
            display_df = df_tab5_agg.drop(columns=["player_id"], errors="ignore").rename(
                columns=rename_map
            )
            num_cols_disp = display_df.select_dtypes(include="number").columns
            display_df[num_cols_disp] = display_df[num_cols_disp].round(2)

            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "G": st.column_config.NumberColumn("G", format="%d"),
                    "A": st.column_config.NumberColumn("A", format="%d"),
                    "Min": st.column_config.NumberColumn("Min", format="%d"),
                    "PJ": st.column_config.NumberColumn("PJ", format="%d"),
                    "xG": st.column_config.NumberColumn("xG", format="%.2f"),
                    "xAG": st.column_config.NumberColumn("xAG", format="%.2f"),
                },
            )

            # Export CSV
            csv_bytes = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar CSV",
                data=csv_bytes,
                file_name="argentina_jugadores_seleccion.csv",
                mime="text/csv",
            )
    else:
        # Club stats
        try:
            with st.spinner("Cargando estadísticas de club..."):
                df_club = load_player_club_stats()
        except Exception as e:
            st.warning(f"No se pudieron cargar las estadísticas de club: {e}")
            df_club = pd.DataFrame()

        if df_club.empty:
            st.info("Sin datos de estadísticas de club disponibles.")
        else:
            if position_filter != "Todos":
                df_club = df_club[df_club["position"] == position_filter]

            seasons = ["Todas"] + sorted(
                df_club["season"].dropna().unique().tolist(), reverse=True
            )
            selected_season = st.selectbox("Temporada", seasons, key="tab5_season")
            if selected_season != "Todas":
                df_club = df_club[df_club["season"] == selected_season]

            df_club_display = df_club.drop(
                columns=["player_id"], errors="ignore"
            ).sort_values("goals", ascending=False)
            rename_club = {
                "player_name": "Jugador", "position": "Pos", "season": "Temporada",
                "club": "Club", "league": "Liga", "matches": "PJ", "minutes": "Min",
                "goals": "G", "assists": "A", "xg": "xG", "xag": "xAG",
                "shots": "Tiros", "shots_on_target": "SOT",
                "passes_completed": "Pases OK", "pass_pct": "Pase%",
                "key_passes": "K Pases", "progressive_passes": "Prog P",
                "tackles": "Tacles", "interceptions": "Int",
                "saves": "Atajadas", "clean_sheets": "Valla 0",
            }
            df_club_display = df_club_display.rename(columns=rename_club)
            num_club = df_club_display.select_dtypes(include="number").columns
            df_club_display[num_club] = df_club_display[num_club].round(2)

            st.dataframe(
                df_club_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "G": st.column_config.NumberColumn("G", format="%d"),
                    "A": st.column_config.NumberColumn("A", format="%d"),
                    "PJ": st.column_config.NumberColumn("PJ", format="%d"),
                    "Min": st.column_config.NumberColumn("Min", format="%d"),
                },
            )

            csv_club = df_club_display.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar CSV",
                data=csv_club,
                file_name="argentina_jugadores_club.csv",
                mime="text/csv",
            )
