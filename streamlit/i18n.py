"""
streamlit/i18n.py
------------------
Internacionalización — ES / EN.
Uso: from i18n import t, comp_name, get_lang
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Nombres de competencias por idioma (desde nombre en DB)
# ---------------------------------------------------------------------------
COMP_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "FIFA World Cup":                       "Mundial Qatar 2022",
        "Copa América 2024":                    "Copa América 2024",
        "Copa América 2021":                    "Copa América 2021",
        "World Cup Qualifying - CONMEBOL":      "Eliminatorias 2026",
        "World Cup Qualifying 2022 - CONMEBOL": "Eliminatorias Qatar 2022",
    },
    "en": {
        "FIFA World Cup":                       "Qatar 2022 World Cup",
        "Copa América 2024":                    "Copa América 2024",
        "Copa América 2021":                    "Copa América 2021",
        "World Cup Qualifying - CONMEBOL":      "2026 WC Qualifying",
        "World Cup Qualifying 2022 - CONMEBOL": "Qatar 2022 WC Qualifying",
    },
}

# ---------------------------------------------------------------------------
# Traducciones generales + por página
# ---------------------------------------------------------------------------
TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # ── Navegación / sidebar ──────────────────────────────────────────
        "lang_toggle":               "🇺🇸 English",
        "sidebar_header":            "📊 {player}",

        # ── Selectores generales ──────────────────────────────────────────
        "select_player_placeholder": "— Elegir jugador —",
        "select_player_prompt":      "Seleccioná un jugador para continuar",
        "filter_competition":        "Competencia",
        "filter_match":              "Partido",
        "comp_placeholder":          "— Elegir competencia —",
        "match_all":                 "Todos los partidos",
        "match_select_comp_first":   "Primero elegí una competencia",

        # ── Shot Map ──────────────────────────────────────────────────────
        "shot_map_title":            "🎯 Shot Map — Argentina",
        "shot_map_prompt":           "Seleccioná un jugador para ver su shot map",
        "kpi_shots":                 "Disparos",
        "kpi_on_target":             "Al arco",
        "kpi_goals":                 "Goles",
        "kpi_xg_total":              "xG total",
        "kpi_xg_per_goal":           "xG / gol",
        "no_shots":                  "No hay disparos para la selección actual.",
        "legend_color_title":        "Color del disparo",
        "legend_size_title":         "Tamaño del punto = xG  (probabilidad de gol)",
        "xg_label":                  "xG",
        # Outcomes
        "outcome_Goal":              "Gol",
        "outcome_Saved":             "Atajado",
        "outcome_Off T":             "Afuera",
        "outcome_Blocked":           "Bloqueado",
        "outcome_Wayward":           "Desviado",
        "outcome_Post":              "Palo",
        "outcome_Saved to Post":     "Palo/Atajado",

        # ── Heat Map ─────────────────────────────────────────────────────
        "heatmap_title":             "🔥 Heat Map — Argentina",
        "heatmap_prompt":            "Seleccioná un jugador para ver su mapa de calor",
        "filter_activity":           "Tipo de actividad",
        "kpi_total_actions":         "Acciones totales",
        "kpi_matches":               "Partidos",
        "kpi_activity_type":         "Tipo de actividad",
        "no_events":                 "No hay eventos para la selección actual.",
        "colorbar_label":            "Densidad de actividad",
        "legend_section_title":      "¿Qué muestra cada tipo de actividad?",
        "includes_label":            "Incluye:",
        # Grupos de actividad
        "group_all":                 "Toda la actividad",
        "group_ball":                "Con balón",
        "group_passes":              "Pases",
        "group_defense":             "Presión / Defensa",
        # Descripciones
        "group_all_desc":            "Todas las acciones del jugador con coordenadas registradas. Muestra el área total de influencia en la cancha.",
        "group_all_inc":             "Pases, recepciones, carries, disparos, duelos, presiones, intercepciones, bloqueos y recuperaciones.",
        "group_ball_desc":           "Solo las acciones donde el jugador tiene el balón o lo recibe. Ideal para ver las zonas preferidas de toque y conducción.",
        "group_ball_inc":            "Pases, carries (conducciones), disparos, driblings y recepciones de balón.",
        "group_passes_desc":         "Únicamente los pases del jugador. Revela desde qué zonas de la cancha distribuye y su rol en la circulación.",
        "group_passes_inc":          "Pases cortos, largos, progresivos y de ruptura.",
        "group_defense_desc":        "Acciones defensivas. Muestra dónde el jugador aplica presión, gana duelos o recupera el balón.",
        "group_defense_inc":         "Presiones, duelos, intercepciones, bloqueos y recuperaciones de balón.",

        # ── Pass Map ─────────────────────────────────────────────────────
        "passmap_title":             "🔵 Pass Map — Argentina",
        "passmap_prompt":            "Seleccioná un jugador para ver su mapa de pases",
        "coming_soon":               "Próximamente",
    },

    "en": {
        # ── Navegación / sidebar ──────────────────────────────────────────
        "lang_toggle":               "🇦🇷 Español",
        "sidebar_header":            "📊 {player}",

        # ── Selectores generales ──────────────────────────────────────────
        "select_player_placeholder": "— Select a player —",
        "select_player_prompt":      "Select a player to continue",
        "filter_competition":        "Competition",
        "filter_match":              "Match",
        "comp_placeholder":          "— Select competition —",
        "match_all":                 "All matches",
        "match_select_comp_first":   "Select a competition first",

        # ── Shot Map ──────────────────────────────────────────────────────
        "shot_map_title":            "🎯 Shot Map — Argentina",
        "shot_map_prompt":           "Select a player to see their shot map",
        "kpi_shots":                 "Shots",
        "kpi_on_target":             "On Target",
        "kpi_goals":                 "Goals",
        "kpi_xg_total":              "Total xG",
        "kpi_xg_per_goal":           "xG / goal",
        "no_shots":                  "No shots for the current selection.",
        "legend_color_title":        "Shot color",
        "legend_size_title":         "Dot size = xG  (goal probability)",
        "xg_label":                  "xG",
        # Outcomes
        "outcome_Goal":              "Goal",
        "outcome_Saved":             "Saved",
        "outcome_Off T":             "Off Target",
        "outcome_Blocked":           "Blocked",
        "outcome_Wayward":           "Wayward",
        "outcome_Post":              "Post",
        "outcome_Saved to Post":     "Post/Saved",

        # ── Heat Map ─────────────────────────────────────────────────────
        "heatmap_title":             "🔥 Heat Map — Argentina",
        "heatmap_prompt":            "Select a player to see their heat map",
        "filter_activity":           "Activity type",
        "kpi_total_actions":         "Total actions",
        "kpi_matches":               "Matches",
        "kpi_activity_type":         "Activity type",
        "no_events":                 "No events for the current selection.",
        "colorbar_label":            "Activity density",
        "legend_section_title":      "What does each activity type show?",
        "includes_label":            "Includes:",
        # Grupos de actividad
        "group_all":                 "All activity",
        "group_ball":                "On the ball",
        "group_passes":              "Passes",
        "group_defense":             "Pressure / Defense",
        # Descripciones
        "group_all_desc":            "All player actions with registered coordinates. Shows the player's total area of influence on the pitch.",
        "group_all_inc":             "Passes, receptions, carries, shots, duels, pressures, interceptions, blocks and recoveries.",
        "group_ball_desc":           "Only actions where the player has or receives the ball. Ideal for seeing preferred touch and dribbling zones.",
        "group_ball_inc":            "Passes, carries, shots, dribbles and ball receipts.",
        "group_passes_desc":         "Only the player's passes. Reveals from which zones they distribute and their role in build-up play.",
        "group_passes_inc":          "Short, long, progressive and through passes.",
        "group_defense_desc":        "Defensive actions. Shows where the player presses, wins duels or recovers the ball.",
        "group_defense_inc":         "Pressures, duels, interceptions, blocks and ball recoveries.",

        # ── Pass Map ─────────────────────────────────────────────────────
        "passmap_title":             "🔵 Pass Map — Argentina",
        "passmap_prompt":            "Select a player to see their pass map",
        "coming_soon":               "Coming soon",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_lang() -> str:
    return st.session_state.get("lang", "es")


def t(key: str, **kwargs) -> str:
    """Devuelve el string traducido al idioma activo."""
    lang = get_lang()
    text = TRANSLATIONS.get(lang, TRANSLATIONS["es"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def comp_name(db_name: str) -> str:
    """Traduce el nombre de competencia desde el nombre en DB."""
    lang = get_lang()
    return COMP_TRANSLATIONS[lang].get(db_name, db_name)


def render_lang_toggle() -> None:
    """Bandera del idioma DESTINO flotando sobre el botón."""
    current   = get_lang()
    target    = "en" if current == "es" else "es"
    # Mostrar bandera del idioma AL QUE se va a cambiar
    flag_code = "us" if current == "es" else "ar"
    label_btn = "   English" if current == "es" else "   Español"

    st.sidebar.markdown("---")

    st.sidebar.markdown(
        f"""
        <div style="position:relative; height:0; z-index:10; pointer-events:none;">
          <img src="https://flagcdn.com/w40/{flag_code}.png"
               style="position:absolute; left:16px; top:9px;
                      height:20px; border-radius:3px;
                      box-shadow:0 1px 3px rgba(0,0,0,0.5);">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # CSS para alinear el texto a la izquierda (junto a la bandera)
    st.sidebar.markdown("""
        <style>
        div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type button {
            text-align: left !important;
            font-weight: 600 !important;
        }
        </style>""", unsafe_allow_html=True)

    if st.sidebar.button(label_btn, use_container_width=True, key="btn_lang"):
        st.session_state["lang"] = target
        st.rerun()
