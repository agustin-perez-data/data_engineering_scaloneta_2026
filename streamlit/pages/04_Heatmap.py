"""
pages/04_Heatmap.py
Mapa de calor de posiciones — StatsBomb (WC 2022 + Copa América 2024).
"""

import io
import os
import sys

import matplotlib.pyplot as plt
import streamlit as st
from mplsoccer import Pitch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db import query
from i18n import t, comp_name, get_lang

# ---------------------------------------------------------------------------
# Grupos de eventos (claves de traducción → listas de event_type en DB)
# ---------------------------------------------------------------------------
EVENT_GROUP_KEYS = ["group_all", "group_ball", "group_passes", "group_defense"]

EVENT_GROUP_TYPES = {
    "group_all":     ["Pass", "Ball Receipt*", "Carry", "Shot", "Duel",
                      "Dribble", "Interception", "Pressure", "Block",
                      "Clearance", "Ball Recovery"],
    "group_ball":    ["Pass", "Carry", "Shot", "Dribble", "Ball Receipt*"],
    "group_passes":  ["Pass"],
    "group_defense": ["Pressure", "Duel", "Interception", "Block",
                      "Clearance", "Ball Recovery"],
}

EVENT_GROUP_INFO_KEYS = {
    "group_all":     ("group_all_desc",     "group_all_inc"),
    "group_ball":    ("group_ball_desc",    "group_ball_inc"),
    "group_passes":  ("group_passes_desc",  "group_passes_inc"),
    "group_defense": ("group_defense_desc", "group_defense_inc"),
}

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_events_raw():
    df = query("""
        SELECT
            e.player_id,
            p.short_name                                AS player,
            p.position,
            e.event_type,
            e.x,
            e.y,
            fm.date,
            fm.opponent,
            fm.goals_for || '-' || fm.goals_against     AS score,
            dc.name                                     AS competition
        FROM event_statsbomb e
        JOIN dim_player      p  USING (player_id)
        JOIN fact_match      fm USING (match_id)
        JOIN dim_competition dc USING (competition_id)
        WHERE e.x IS NOT NULL AND e.y IS NOT NULL
        ORDER BY fm.date
    """)
    df["date"] = df["date"].astype(str).str[:10]
    return df

def load_events():
    df = load_events_raw().copy()
    df["competition"] = df["competition"].map(comp_name)
    return df

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(t("heatmap_title"))
st.markdown("---")

df_all = load_events()
lang   = get_lang()

if df_all.empty:
    st.warning("No data available.")
    st.stop()

# ---------------------------------------------------------------------------
# Selector de jugador
# ---------------------------------------------------------------------------
players_available = sorted(df_all["player"].unique().tolist())

# Stats para el estado vacío
total_events = len(df_all)
top_active   = df_all.groupby("player").size().idxmax()
top_ev_count = df_all.groupby("player").size().max()
competitions = df_all["competition"].nunique()
passes_count = int((df_all["event_type"] == "Pass").sum())

# Selector + KPIs en la misma fila
col_sel, _, ka1, ka2, ka3 = st.columns([1.6, 0.4, 1, 1, 1])
with col_sel:
    st.markdown("<div style='padding-right: 24px;'>", unsafe_allow_html=True)
    player_sel = st.selectbox(
        t("select_player_placeholder"),
        options=[t("select_player_placeholder")] + players_available,
        index=0,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
ka1.metric(
    "Total eventos" if lang == "es" else "Total events",
    f"{total_events:,}",
    f"{passes_count:,} " + ("pases" if lang == "es" else "passes"),
)
ka2.metric(
    "Jugador más activo" if lang == "es" else "Most active player",
    top_active,
    f"{top_ev_count:,} " + ("eventos" if lang == "es" else "events"),
)
ka3.metric(
    "Competencias" if lang == "es" else "Competitions",
    competitions,
    "WC 2022 + Copa América 2024",
)
st.markdown("---")

if player_sel == t("select_player_placeholder"):

    # ── Cancha completa vacía decorativa ───────────────────────────────────
    fig_e, ax_e = plt.subplots(figsize=(10, 5), facecolor="#0d1117")
    ax_e.set_facecolor("#0d1117")
    pitch_e = Pitch(
        pitch_type="statsbomb", pitch_color="#1a2332",
        line_color="#74ACDF", linewidth=1.2, goal_type="box",
    )
    pitch_e.draw(ax=ax_e)
    ax_e.text(60, 40, t("heatmap_prompt"),
              color="#4B5563", fontsize=16, ha="center", va="center",
              fontweight="bold", alpha=0.9)
    ax_e.text(60, 33,
              f"↑  {len(players_available)} " + ("jugadores disponibles" if lang == "es" else "players available"),
              color="#374151", fontsize=11, ha="center", va="center", alpha=0.8)
    fig_e.tight_layout()
    buf_e = io.BytesIO()
    fig_e.savefig(buf_e, format="png", dpi=120, bbox_inches="tight", facecolor="#0d1117")
    buf_e.seek(0)
    plt.close(fig_e)

    st.image(buf_e, use_container_width=True)
    st.stop()

df_player = df_all[df_all["player"] == player_sel].copy()

# ---------------------------------------------------------------------------
# Filtros horizontales
# ---------------------------------------------------------------------------
competitions = sorted(df_player["competition"].unique().tolist())
group_labels = [t(k) for k in EVENT_GROUP_KEYS]

fc, fm_col, fa_col = st.columns(3)

with fc:
    comp_sel = st.selectbox(t("filter_competition"),
                            [t("comp_placeholder")] + competitions)

if comp_sel == t("comp_placeholder"):
    match_sel = None
    with fm_col:
        st.selectbox(t("filter_match"),
                     [t("match_select_comp_first")], disabled=True)
    df_by_comp = df_player.copy()
else:
    df_by_comp = df_player[df_player["competition"] == comp_sel]
    match_options = [t("match_all")] + [
        f"{r.date}  {r.opponent}  ({r.score})"
        for r in df_by_comp[["date", "opponent", "score"]]
            .drop_duplicates().sort_values("date").itertuples()
    ]
    with fm_col:
        match_sel = st.selectbox(t("filter_match"), match_options)

with fa_col:
    group_sel_label = st.selectbox(t("filter_activity"), group_labels)
group_key = EVENT_GROUP_KEYS[group_labels.index(group_sel_label)]

# ---------------------------------------------------------------------------
# Aplicar filtros
# ---------------------------------------------------------------------------
df_filtered = df_by_comp.copy()
opp_sel = date_sel = None

if match_sel and match_sel not in (None, t("match_all")):
    date_sel = match_sel.split("  ")[0]
    opp_sel  = match_sel.split("  ")[1]
    df_filtered = df_filtered[
        (df_filtered["date"] == date_sel) &
        (df_filtered["opponent"] == opp_sel)
    ]

df_filtered = df_filtered[
    df_filtered["event_type"].isin(EVENT_GROUP_TYPES[group_key])
]

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric(t("kpi_total_actions"), len(df_filtered))
c2.metric(t("kpi_matches"),       df_filtered.groupby(["date", "opponent"]).ngroups)
c3.metric(t("kpi_activity_type"), group_sel_label)

st.markdown("---")

if df_filtered.empty:
    st.info(t("no_events"))
    st.stop()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 8), facecolor="#0d1117")
ax.set_facecolor("#0d1117")

pitch = Pitch(
    pitch_type="statsbomb",
    pitch_color="#1a2332",
    line_color="#74ACDF",
    linewidth=1.2,
    goal_type="box",
)
pitch.draw(ax=ax)

pitch.kdeplot(
    df_filtered["x"], df_filtered["y"],
    ax=ax, cmap="YlOrRd", levels=100,
    fill=True, alpha=0.72, thresh=0.05, bw_adjust=0.7,
)
pitch.scatter(
    df_filtered["x"], df_filtered["y"],
    ax=ax, s=12, color="white", alpha=0.18, zorder=2,
)

# Título
if match_sel and match_sel not in (None, t("match_all")) and opp_sel:
    subtitle = f"vs {opp_sel}  ({date_sel})"
elif comp_sel != t("comp_placeholder"):
    subtitle = comp_sel
else:
    subtitle = "WC 2022 + Copa América 2024"

ax.set_title(f"{player_sel} — {subtitle}",
             color="white", fontsize=13, fontweight="bold", pad=14)

# Etiquetas de arcos (cancha horizontal: izquierda = Argentina, derecha = rival)
from i18n import get_lang as _get_lang
_lang = _get_lang()
ax.text(-0.01, 0.5,
        "🥅 " + ("Argentina" if _lang == "es" else "Argentina"),
        transform=ax.transAxes, ha="right", va="center",
        color="#74ACDF", fontsize=8, fontweight="bold", rotation=90)
ax.text(1.01, 0.5,
        ("Rival" if _lang == "es" else "Opponent") + " 🥅",
        transform=ax.transAxes, ha="left", va="center",
        color="#F6B40E", fontsize=8, fontweight="bold", rotation=90)

# Colorbar
sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=0, vmax=1))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.02, pad=0.02)
cbar.set_label(t("colorbar_label"), color="white", fontsize=9)
cbar.ax.yaxis.set_tick_params(color="white")
plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white", fontsize=7)
cbar.ax.set_facecolor("#0d1117")

fig.tight_layout()
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
buf.seek(0)
plt.close(fig)

_, col_center, _ = st.columns([1, 4, 1])
with col_center:
    st.image(buf, use_container_width=True)

# ---------------------------------------------------------------------------
# Descripciones de los tipos de actividad
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(f"#### {t('legend_section_title')}")

cols = st.columns(len(EVENT_GROUP_KEYS))
for col, key in zip(cols, EVENT_GROUP_KEYS):
    is_active    = key == group_key
    border_color = "#F6B40E" if is_active else "#1F2937"
    bg_color     = "rgba(246,180,14,0.08)" if is_active else "rgba(255,255,255,0.03)"
    title_color  = "#F6B40E" if is_active else "#74ACDF"
    desc_key, inc_key = EVENT_GROUP_INFO_KEYS[key]
    col.markdown(
        f"""
        <div style="
            border: 1.5px solid {border_color};
            border-radius: 8px;
            padding: 14px;
            background: {bg_color};
            height: 100%;
        ">
            <div style="color:{title_color}; font-weight:700; font-size:0.9rem; margin-bottom:6px;">
                {t(key)}
            </div>
            <div style="color:#D1D5DB; font-size:0.8rem; margin-bottom:8px;">
                {t(desc_key)}
            </div>
            <div style="color:#9CA3AF; font-size:0.75rem;">
                <span style="color:#6B7280;">{t('includes_label')}</span> {t(inc_key)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
