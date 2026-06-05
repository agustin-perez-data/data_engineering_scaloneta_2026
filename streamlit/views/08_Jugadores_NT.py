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

st.title("👤 " + ("Jugadores" if lang == "es" else "Players"))
st.markdown("---")

UUIDS = {
    "es": "0c7d95f9-06e1-4e36-a9e4-fa71022f003f",
    "en": "7ad5f909-ac53-4a9d-9f1e-1c2cac2072f7",
}

render_metabase_dashboard(UUIDS[lang])
