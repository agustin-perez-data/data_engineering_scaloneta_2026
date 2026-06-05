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

st.title("📊 " + ("Plantel 2024-25" if lang == "es" else "2024-25 Squad"))
st.markdown("---")

UUIDS = {
    "es": "aa8f31ee-12f9-40ae-9ced-7fabbd9c243d",
    "en": "93f69af0-f26a-42bf-9ea5-b0078c1c6884",
}

render_metabase_dashboard(UUIDS[lang])
