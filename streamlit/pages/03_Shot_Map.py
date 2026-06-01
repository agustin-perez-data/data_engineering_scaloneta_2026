"""
pages/03_Shot_Map.py
Shot map de Argentina — StatsBomb (WC 2022 + Copa América 2024).
"""

import io
import os
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import streamlit as st
from mplsoccer import VerticalPitch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db import query
from i18n import t, comp_name, get_lang

# ---------------------------------------------------------------------------
# Colores por outcome (fijos, no dependen del idioma)
# ---------------------------------------------------------------------------
OUTCOME_COLORS = {
    "Goal":          "#F6B40E",
    "Saved":         "#74ACDF",
    "Off T":         "#6B7280",
    "Blocked":       "#EF4444",
    "Wayward":       "#4B5563",
    "Post":          "#F97316",
    "Saved to Post": "#C2410C",
}

def outcome_label(outcome: str) -> str:
    return t(f"outcome_{outcome}")

# ---------------------------------------------------------------------------
# Carga de datos (raw, sin renombrar competencias)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_shots_raw():
    df = query("""
        SELECT
            e.player_id,
            p.short_name                                AS player,
            p.position,
            e.minute,
            e.period,
            e.x,
            e.y,
            e.outcome,
            COALESCE(e.xg, 0)                           AS xg,
            fm.date,
            fm.opponent,
            fm.goals_for || '-' || fm.goals_against     AS score,
            dc.name                                     AS competition
        FROM event_statsbomb e
        JOIN dim_player      p  USING (player_id)
        JOIN fact_match      fm USING (match_id)
        JOIN dim_competition dc USING (competition_id)
        WHERE e.event_type = 'Shot'
        ORDER BY fm.date, e.minute
    """)
    df["date"] = df["date"].astype(str).str[:10]
    return df

def load_shots():
    df = load_shots_raw().copy()
    df["competition"] = df["competition"].map(comp_name)
    return df

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(t("shot_map_title"))
st.markdown("---")

df_all = load_shots()
lang   = get_lang()

if df_all.empty:
    st.warning("No data available.")
    st.stop()

# ---------------------------------------------------------------------------
# Selector de jugador
# ---------------------------------------------------------------------------
players_available = sorted(df_all["player"].unique().tolist())

# Calcular stats para el estado vacío (se necesitan antes del selector)
total_shots  = len(df_all)
total_goals  = int((df_all["outcome"] == "Goal").sum())
conv_pct     = round(total_goals / total_shots * 100) if total_shots else 0
top_shooter  = df_all.groupby("player").size().idxmax()
top_sh_count = df_all.groupby("player").size().max()
top_xg_name  = df_all.groupby("player")["xg"].sum().idxmax()
top_xg_val   = round(df_all.groupby("player")["xg"].sum().max(), 2)

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
    "Total disparos" if lang == "es" else "Total shots",
    f"{total_shots}",
    f"{total_goals} goles ({conv_pct}%)" if lang == "es" else f"{total_goals} goals ({conv_pct}%)",
)
ka2.metric(
    "Más disparos" if lang == "es" else "Most shots",
    top_shooter,
    f"{top_sh_count} disparos" if lang == "es" else f"{top_sh_count} shots",
)
ka3.metric(
    "Mayor xG acumulado" if lang == "es" else "Highest xG",
    top_xg_name,
    f"xG {top_xg_val}",
)
st.markdown("---")

if player_sel == t("select_player_placeholder"):

    # ── Media cancha vacía decorativa ──────────────────────────────────────
    fig_e, ax_e = plt.subplots(figsize=(9, 11), facecolor="#0d1117")
    ax_e.set_facecolor("#0d1117")
    pitch_e = VerticalPitch(
        pitch_type="statsbomb", pitch_color="#1a2332",
        line_color="#74ACDF", half=True, linewidth=1.2, goal_type="box",
    )
    pitch_e.draw(ax=ax_e)
    ax_e.text(40, 90, t("shot_map_prompt"),
              color="#4B5563", fontsize=14, ha="center", va="center",
              fontweight="bold", alpha=0.9)
    ax_e.text(40, 83,
              f"↑  {len(players_available)} " + ("jugadores disponibles" if lang == "es" else "players available"),
              color="#374151", fontsize=10, ha="center", va="center", alpha=0.8)
    fig_e.tight_layout()
    buf_e = io.BytesIO()
    fig_e.savefig(buf_e, format="png", dpi=120, bbox_inches="tight", facecolor="#0d1117")
    buf_e.seek(0)
    plt.close(fig_e)

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.image(buf_e, use_container_width=True)
    st.stop()

df_player = df_all[df_all["player"] == player_sel].copy()

# ---------------------------------------------------------------------------
# Filtros horizontales
# ---------------------------------------------------------------------------
competitions = sorted(df_player["competition"].unique().tolist())
fc, fm_col = st.columns(2)

with fc:
    comp_sel = st.selectbox(t("filter_competition"),
                            [t("comp_placeholder")] + competitions,
                            label_visibility="visible")

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

# Aplicar filtro de partido
df_filtered = df_by_comp.copy()
opp_sel = date_sel = None
if match_sel and match_sel not in (None, t("match_all")):
    date_sel = match_sel.split("  ")[0]
    opp_sel  = match_sel.split("  ")[1]
    df_filtered = df_filtered[
        (df_filtered["date"] == date_sel) &
        (df_filtered["opponent"] == opp_sel)
    ]

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total      = len(df_filtered)
goals      = int((df_filtered["outcome"] == "Goal").sum())
on_tgt     = int(df_filtered["outcome"].isin(["Goal", "Saved", "Saved to Post"]).sum())
xg_total   = float(df_filtered["xg"].sum())
on_tgt_pct = round(on_tgt / total * 100) if total else 0
xg_pgol    = round(xg_total / goals, 2) if goals else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(t("kpi_shots"),       total)
c2.metric(t("kpi_on_target"),   f"{on_tgt} ({on_tgt_pct}%)")
c3.metric(t("kpi_goals"),       goals)
c4.metric(t("kpi_xg_total"),    f"{xg_total:.2f}")
c5.metric(t("kpi_xg_per_goal"), f"{xg_pgol:.2f}" if xg_pgol else "—")

st.markdown("---")

if df_filtered.empty:
    st.info(t("no_shots"))
    st.stop()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 11), facecolor="#0d1117")
ax.set_facecolor("#0d1117")

pitch = VerticalPitch(
    pitch_type="statsbomb",
    pitch_color="#1a2332",
    line_color="#74ACDF",
    half=True,
    linewidth=1.2,
    goal_type="box",
)
pitch.draw(ax=ax)

for _, shot in df_filtered.iterrows():
    color   = OUTCOME_COLORS.get(shot["outcome"], "#6B7280")
    size    = max(80, min(1800, float(shot["xg"]) * 2500))
    is_goal = shot["outcome"] == "Goal"
    ax.scatter(
        shot["y"], shot["x"],
        s=size, c=color,
        edgecolors="#FFFFFF" if is_goal else color,
        linewidths=1.8 if is_goal else 0.5,
        alpha=0.9 if is_goal else 0.65,
        zorder=5 if is_goal else 3,
    )

# Título
if match_sel and match_sel not in (None, t("match_all")) and opp_sel:
    subtitle = f"vs {opp_sel}  ({date_sel})"
elif comp_sel != t("comp_placeholder"):
    subtitle = comp_sel
else:
    subtitle = "WC 2022 + Copa América 2024"

ax.set_title(f"{player_sel} — {subtitle}",
             color="white", fontsize=13, fontweight="bold", pad=12)

# Leyenda — axes separado debajo de la cancha
fig.subplots_adjust(bottom=0.22)
legend_ax = fig.add_axes([0.05, 0.01, 0.90, 0.18])
legend_ax.set_facecolor("#111827")
legend_ax.set_xlim(0, 1); legend_ax.set_ylim(0, 1); legend_ax.axis("off")
for spine in legend_ax.spines.values():
    spine.set_visible(True); spine.set_color("#74ACDF"); spine.set_linewidth(1)

# Fila 1: colores de outcome
outcomes_in_plot = df_filtered["outcome"].unique()
outcome_items = [
    (OUTCOME_COLORS[o], outcome_label(o))
    for o in OUTCOME_COLORS
    if o in outcomes_in_plot
]
n = len(outcome_items)
if n:
    legend_ax.text(0.5, 0.95, t("legend_color_title"),
                   ha="center", va="top", color="#74ACDF",
                   fontsize=9, fontweight="bold", transform=legend_ax.transAxes)
    for i, (color, label) in enumerate(outcome_items):
        x = (i + 0.5) / n
        legend_ax.scatter([x], [0.62], s=220, c=color,
                          transform=legend_ax.transAxes, zorder=3, clip_on=False)
        legend_ax.text(x, 0.42, label, ha="center", va="top",
                       color="white", fontsize=8.5, transform=legend_ax.transAxes)

# Fila 2: referencia de tamaños xG
legend_ax.text(0.5, 0.28, t("legend_size_title"),
               ha="center", va="top", color="#74ACDF",
               fontsize=9, fontweight="bold", transform=legend_ax.transAxes)
for i, (xg_val, lbl) in enumerate([(0.05, "0.05"), (0.15, "0.15"), (0.35, "0.35"), (0.65, "0.65")]):
    x = 0.14 + i * 0.22
    legend_ax.scatter([x], [0.10], s=max(80, min(1800, xg_val * 2500)),
                      c="#74ACDF", alpha=0.75,
                      transform=legend_ax.transAxes, zorder=3, clip_on=False)
    legend_ax.text(x, -0.04, f"{t('xg_label')} {lbl}", ha="center", va="top",
                   color="#9CA3AF", fontsize=8, transform=legend_ax.transAxes)

buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
buf.seek(0)
plt.close(fig)

_, col_center, _ = st.columns([1, 2, 1])
with col_center:
    st.image(buf, use_container_width=True)
