import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang, t

lang = get_lang()

# Fondo claro para integrar con Metabase
st.markdown("""
<style>
.stApp { background: #f9fafb !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #f9fafb !important; }
h1, h2, h3 { color: #1a3a5c !important; }
hr { border-color: #d1d5db !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 " + ("Plantel 2024-25" if lang == "es" else "2024-25 Squad"))
st.markdown("---")

UUIDS = {
    "es": "aa8f31ee-12f9-40ae-9ced-7fabbd9c243d",
    "en": "93f69af0-f26a-42bf-9ea5-b0078c1c6884",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}",
    height=1200,
    scrolling=True,
)
