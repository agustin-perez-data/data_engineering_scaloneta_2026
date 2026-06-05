import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang

lang = get_lang()

st.markdown("""
<style>
.stApp {
    background: linear-gradient(160deg, #050f1c 0%, #0b1f3a 50%, #071428 100%) !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: transparent !important;
}
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
