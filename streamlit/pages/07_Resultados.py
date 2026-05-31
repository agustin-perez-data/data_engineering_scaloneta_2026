import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang

lang = get_lang()

st.title("📈 " + ("Resultados Selección" if lang == "es" else "NT Results"))
st.markdown("---")

UUIDS = {
    "es": "7f48ff7f-c0ab-460d-9024-36c3a4b1dd50",
    "en": "3c5f25a2-cf21-47a5-b19e-9bddbc2e0bf4",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}",
    height=1200,
    scrolling=True,
)
