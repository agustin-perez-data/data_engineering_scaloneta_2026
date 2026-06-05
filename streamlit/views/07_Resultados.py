import os, sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang
from utils import render_metabase_dashboard

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

render_metabase_dashboard(UUIDS[lang])
