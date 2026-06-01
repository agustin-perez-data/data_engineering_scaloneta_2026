"""
pages/05_Pass_Map.py
Mapa de pases — StatsBomb (WC 2022 + Copa América 2024).
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

COMPLETED_COLOR  = "#74ACDF"
INCOMPLETE_COLOR = "#EF4444"
KEY_PASS_COLOR   = "#F6B40E"

INCOMPLETE_OUTCOMES = {"Incomplete", "Out", "Pass Offside", "Injury Clearance", "Unknown"}

def is_progressive(row) -> bool:
    return (row["end_x"] - row["x"]) >= 10

PASS_FILTER_KEYS = ["pass_all", "pass_completed", "pass_progressive", "pass_final_third"]

PASS_FILTER_LABELS = {
    "es": {
        "pass_all":         "Todos los pases",
        "pass_completed":   "Completados",
        "pass_progressive": "Progresivos",
        "pass_final_third": "Último tercio",
    },
    "en": {
        "pass_all":         "All passes",
        "pass_completed":   "Completed",
        "pass_progressive": "Progressive",
        "pass_final_third": "Final third",
    },
}

PASS_FILTER_DESCRIPTIONS = {
    "es": {
        "pass_all":         ("Todos los pases realizados.", "Celeste = completado, Rojo = incompleto."),
        "pass_completed":   ("Solo pases que llegaron al compañero.", "Excluye interceptados, fuera de campo y offside."),
        "pass_progressive": ("Pases completados que avanzan ≥ 10 metros hacia el arco rival.", "Indica la capacidad de progresar con el balón."),
        "pass_final_third": ("Pases completados cuyo destino está en el último tercio (x ≥ 80).", "Zona de máximo peligro: los 40 metros finales antes del arco rival."),
    },
    "en": {
        "pass_all":         ("All passes attempted.", "Blue = completed, Red = incomplete."),
        "pass_completed":   ("Only passes that reached a teammate.", "Excludes intercepted, out-of-play and offside passes."),
        "pass_progressive": ("Completed passes advancing ≥ 10 meters toward the opponent's goal.", "Indicates the ability to progress with the ball."),
        "pass_final_third": ("Completed passes whose destination is in the final third (x ≥ 80).", "The most dangerous 40 meters before the opponent's goal."),
    },
}

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_passes_raw():
    return query("""
        SELECT
            e.player_id,
            p.short_name                                AS player,
            e.x, e.y, e.end_x, e.end_y,
            e.outcome,
            fm.date,
            fm.opponent,
            fm.goals_for || '-' || fm.goals_against     AS score,
            dc.name                                     AS competition
        FROM event_statsbomb e
        JOIN dim_player      p  USING (player_id)
        JOIN fact_match      fm USING (match_id)
        JOIN dim_competition dc USING (competition_id)
        WHERE e.event_type = 'Pass'
          AND e.end_x IS NOT NULL
        ORDER BY fm.date
    """)

def load_passes():
    df = load_passes_raw().copy()
    df["date"]        = df["date"].astype(str).str[:10]
    df["competition"] = df["competition"].map(comp_name)
    df["completed"]   = ~df["outcome"].isin(INCOMPLETE_OUTCOMES)
    df["progressive"] = df.apply(is_progressive, axis=1) & df["completed"]
    df["final_third"] = (df["end_x"] >= 80) & df["completed"]
    return df

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(t("passmap_title"))
st.markdown("---")

df_all = load_passes()
lang   = get_lang()

if df_all.empty:
    st.warning("No data available.")
    st.stop()

# ---------------------------------------------------------------------------
# Selector de jugador
# ---------------------------------------------------------------------------
players_available = sorted(df_all["player"].unique().tolist())

# Stats para el estado vacío
total_passes = len(df_all)
top_passer   = df_all.groupby("player").size().idxmax()
top_count    = df_all.groupby("player").size().max()
top_prog     = df_all[df_all["progressive"]].groupby("player").size().idxmax()

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
    "Total pases" if lang == "es" else "Total passes",
    f"{total_passes:,}",
)
ka2.metric(
    "Top pasador" if lang == "es" else "Top passer",
    top_passer,
    f"{top_count} pases" if lang == "es" else f"{top_count} passes",
)
ka3.metric(
    "Más progresivo" if lang == "es" else "Most progressive",
    top_prog,
    "mayor cant. pases progresivos" if lang == "es" else "most progressive passes",
)
st.markdown("---")

if player_sel == t("select_player_placeholder"):

    # ── Cancha vacía decorativa ────────────────────────────────────────────
    import matplotlib
    matplotlib.use("Agg")

    fig_empty, ax_empty = plt.subplots(figsize=(16, 8), facecolor="#0d1117")
    ax_empty.set_facecolor("#0d1117")
    pitch_empty = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a2332",
        line_color="#74ACDF",
        linewidth=1.2,
        goal_type="box",
    )
    pitch_empty.draw(ax=ax_empty)
    ax_empty.text(
        60, 40,
        t("passmap_prompt"),
        color="#4B5563", fontsize=16, ha="center", va="center",
        fontweight="bold", alpha=0.9,
    )
    ax_empty.text(
        60, 33,
        "↑  " + (f"{len(players_available)} jugadores disponibles"
                  if lang == "es" else f"{len(players_available)} players available"),
        color="#374151", fontsize=11, ha="center", va="center", alpha=0.8,
    )
    fig_empty.tight_layout()
    buf_empty = io.BytesIO()
    fig_empty.savefig(buf_empty, format="png", dpi=120,
                      bbox_inches="tight", facecolor="#0d1117")
    buf_empty.seek(0)
    plt.close(fig_empty)

    st.image(buf_empty, use_container_width=True)
    st.stop()

df_player = df_all[df_all["player"] == player_sel].copy()

# ---------------------------------------------------------------------------
# Filtros horizontales
# ---------------------------------------------------------------------------
filter_label_map   = PASS_FILTER_LABELS[lang]
pass_filter_labels = [filter_label_map[k] for k in PASS_FILTER_KEYS]
competitions       = sorted(df_player["competition"].unique().tolist())

fc, fm_col, fp_col = st.columns(3)

with fc:
    comp_sel = st.selectbox(t("filter_competition"),
                            [t("comp_placeholder")] + competitions)

if comp_sel == t("comp_placeholder"):
    match_sel  = None
    df_by_comp = None
    with fm_col:
        st.selectbox(t("filter_match"), [t("match_select_comp_first")], disabled=True)
else:
    df_by_comp = df_player[df_player["competition"] == comp_sel]
    match_options = [t("match_all")] + [
        f"{r.date}  {r.opponent}  ({r.score})"
        for r in df_by_comp[["date", "opponent", "score"]]
            .drop_duplicates().sort_values("date").itertuples()
    ]
    with fm_col:
        match_sel = st.selectbox(t("filter_match"), match_options)

with fp_col:
    pass_filter_label = st.selectbox(
        "Tipo de pase" if lang == "es" else "Pass type",
        pass_filter_labels,
    )
pass_filter_key = PASS_FILTER_KEYS[pass_filter_labels.index(pass_filter_label)]

# ---------------------------------------------------------------------------
# Bloquear si no eligió competencia
# ---------------------------------------------------------------------------
if df_by_comp is None:
    st.markdown(
        f"<div style='text-align:center; color:#6B7280; margin-top:40px; font-size:1.1rem;'>"
        f"{'Seleccioná una competencia para ver los pases' if lang == 'es' else 'Select a competition to see the passes'}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.stop()

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

if pass_filter_key == "pass_completed":
    df_filtered = df_filtered[df_filtered["completed"]]
elif pass_filter_key == "pass_progressive":
    df_filtered = df_filtered[df_filtered["progressive"]]
elif pass_filter_key == "pass_final_third":
    df_filtered = df_filtered[df_filtered["final_third"]]

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total_f     = len(df_filtered)
completed   = int(df_filtered["completed"].sum())
comp_pct    = round(completed / total_f * 100) if total_f else 0
progressive = int(df_filtered["progressive"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pases"       if lang == "es" else "Passes",      total_f)
c2.metric("Completados" if lang == "es" else "Completed",   completed)
c3.metric("Precisión"   if lang == "es" else "Accuracy",    f"{comp_pct}%")
c4.metric("Progresivos" if lang == "es" else "Progressive", progressive)

st.markdown("---")

if df_filtered.empty:
    st.info("No hay pases para la selección actual." if lang == "es"
            else "No passes for the current selection.")
    st.stop()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 10), facecolor="#0d1117")
ax.set_facecolor("#0d1117")

pitch = Pitch(
    pitch_type="statsbomb",
    pitch_color="#1a2332",
    line_color="#74ACDF",
    linewidth=1.2,
    goal_type="box",
)
pitch.draw(ax=ax)

n          = len(df_filtered)
base_alpha = max(0.40, min(0.85, 60 / n)) if n > 0 else 0.65
# Ajuste de tamaño de flecha según volumen — mínimos más altos para mayor visibilidad
hw = max(5.5, min(10.0, 250 / n))  # headwidth
hl = max(4.0, min(8.0,  180 / n))  # headlength
lw = max(1.5, min(3.5,   55 / n))  # linewidth

def _arrows(df_sub, color, alpha, zorder=4):
    if df_sub.empty:
        return
    pitch.arrows(
        df_sub["x"], df_sub["y"],
        df_sub["end_x"], df_sub["end_y"],
        ax=ax, width=lw, headwidth=hw, headlength=hl,
        color=color, alpha=alpha, zorder=zorder,
    )

if pass_filter_key == "pass_all":
    inc  = df_filtered[~df_filtered["completed"]]
    comp = df_filtered[df_filtered["completed"]]
    _arrows(inc,  INCOMPLETE_COLOR, base_alpha * 0.9, zorder=2)
    _arrows(comp, COMPLETED_COLOR,  base_alpha,       zorder=4)
    legend_elements = [
        plt.Line2D([0], [0], color=COMPLETED_COLOR, lw=2,
                   label="Completado" if lang == "es" else "Completed"),
        plt.Line2D([0], [0], color=INCOMPLETE_COLOR, lw=2,
                   label="Incompleto" if lang == "es" else "Incomplete"),
    ]
    ax.legend(handles=legend_elements, loc="lower center", ncol=2,
              fontsize=9, framealpha=0.2, labelcolor="white",
              facecolor="#0d1117", edgecolor="#74ACDF")

elif pass_filter_key == "pass_final_third":
    _arrows(df_filtered, KEY_PASS_COLOR,
            min(1.0, max(0.20, base_alpha * 1.4)), zorder=4)
    pitch.scatter(df_filtered["end_x"], df_filtered["end_y"], ax=ax,
                  s=50, color=KEY_PASS_COLOR, marker="*", alpha=0.85, zorder=6)
else:
    color = COMPLETED_COLOR if pass_filter_key == "pass_completed" else "#A78BFA"
    _arrows(df_filtered, color, base_alpha, zorder=4)

# Título
if match_sel and match_sel not in (None, t("match_all")) and opp_sel:
    subtitle = f"vs {opp_sel}  ({date_sel})"
elif comp_sel != t("comp_placeholder"):
    subtitle = comp_sel
else:
    subtitle = "WC 2022 + Copa América 2024"

ax.set_title(f"{player_sel} — {subtitle}",
             color="white", fontsize=13, fontweight="bold", pad=12)

# Etiquetas de arcos (cancha horizontal: izquierda = Argentina, derecha = rival)
ax.text(-0.01, 0.5,
        "🥅 " + ("Argentina" if lang == "es" else "Argentina"),
        transform=ax.transAxes, ha="right", va="center",
        color="#74ACDF", fontsize=8, fontweight="bold", rotation=90)
ax.text(1.01, 0.5,
        ("Rival" if lang == "es" else "Opponent") + " 🥅",
        transform=ax.transAxes, ha="left", va="center",
        color="#F6B40E", fontsize=8, fontweight="bold", rotation=90)

fig.tight_layout()
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
buf.seek(0)
plt.close(fig)

st.image(buf, use_container_width=True)

# ---------------------------------------------------------------------------
# Panel inferior — descripción + stats de pases
# ---------------------------------------------------------------------------
st.markdown("---")
desc, detail = PASS_FILTER_DESCRIPTIONS[lang][pass_filter_key]

col_desc, col_stats = st.columns([3, 2])

with col_desc:
    st.markdown(
        f"""
        <div style="
            border: 1.5px solid #F6B40E;
            border-radius: 8px;
            padding: 16px 20px;
            background: rgba(246,180,14,0.06);
            height: 100%;
        ">
            <div style="color:#F6B40E; font-weight:700; font-size:1rem; margin-bottom:8px;">
                {pass_filter_label}
            </div>
            <div style="color:#D1D5DB; font-size:0.88rem; margin-bottom:6px;">{desc}</div>
            <div style="color:#9CA3AF; font-size:0.82rem;">
                <span style="color:#6B7280;">{'Nota' if lang == 'es' else 'Note'}:</span> {detail}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_stats:
    total_all  = len(df_by_comp)
    comp_all   = int(df_by_comp["completed"].sum())
    prog_all   = int(df_by_comp["progressive"].sum())
    third_all  = int(df_by_comp["final_third"].sum())
    pct_comp   = round(comp_all / total_all * 100) if total_all else 0
    pct_prog   = round(prog_all / total_all * 100) if total_all else 0
    pct_third  = round(third_all / total_all * 100) if total_all else 0

    label_all   = "Total de pases"   if lang == "es" else "Total passes"
    label_comp  = "Completados"      if lang == "es" else "Completed"
    label_prog  = "Progresivos"      if lang == "es" else "Progressive"
    label_third = "Último tercio"    if lang == "es" else "Final third"

    st.markdown(
        f"""
        <div style="
            border: 1.5px solid #1F2937;
            border-radius: 8px;
            padding: 16px 20px;
            background: rgba(116,172,223,0.05);
        ">
            <div style="color:#74ACDF; font-weight:700; font-size:0.9rem; margin-bottom:12px;">
                {'Desglose de pases' if lang == 'es' else 'Pass breakdown'}
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label_all}</span>
                <span style="color:white; font-weight:600;">{total_all}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label_comp}</span>
                <span style="color:#74ACDF; font-weight:600;">{comp_all} <span style="color:#6B7280; font-weight:400;">({pct_comp}%)</span></span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label_prog}</span>
                <span style="color:#A78BFA; font-weight:600;">{prog_all} <span style="color:#6B7280; font-weight:400;">({pct_prog}%)</span></span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label_third}</span>
                <span style="color:#F6B40E; font-weight:600;">{third_all} <span style="color:#6B7280; font-weight:400;">({pct_third}%)</span></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
