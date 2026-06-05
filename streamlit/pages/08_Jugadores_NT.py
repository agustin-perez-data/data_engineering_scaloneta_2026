import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang

lang = get_lang()

st.markdown("""
<style>
.stApp { background: #2d2d2d !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #2d2d2d !important;
    padding-top: 0.5rem !important;
}
[data-testid="stMainBlockContainer"] { padding-top: 0.5rem !important; }
h1, h2, h3 { color: #e0e0e0 !important; }
hr { border-color: #444 !important; margin: 0.3rem 0 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

st.title("👤 " + ("Jugadores" if lang == "es" else "Players"))
st.markdown("---")

UUIDS = {
    "es": "0c7d95f9-06e1-4e36-a9e4-fa71022f003f",
    "en": "7ad5f909-ac53-4a9d-9f1e-1c2cac2072f7",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}#theme=night",
    height=1200,
    scrolling=True,
)
