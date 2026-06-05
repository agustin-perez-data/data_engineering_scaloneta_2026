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

st.title("📈 " + ("Resultados Selección" if lang == "es" else "NT Results"))
st.markdown("---")

UUIDS = {
    "es": "e18eca5e-3627-43cc-97ae-0e56d0260465",
    "en": "61bb4124-93b8-4b10-9865-889a09a76211",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}#theme=night",
    height=1200,
    scrolling=True,
)
