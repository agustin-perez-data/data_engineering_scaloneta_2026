import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang, t

lang = get_lang()

st.title("📊 " + ("Plantel 2024-25" if lang == "es" else "2024-25 Squad"))
st.markdown("---")

UUIDS = {
    "es": "ed6ce758-2d9c-4a0c-a262-7f5522afad4b",
    "en": "b455768f-e28e-47e2-9080-49ffd68885de",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}",
    height=1200,
    scrolling=True,
)
