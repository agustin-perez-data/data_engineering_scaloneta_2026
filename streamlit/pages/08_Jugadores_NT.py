import os, sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from i18n import get_lang

lang = get_lang()

st.title("👤 " + ("Jugadores NT" if lang == "es" else "NT Players"))
st.markdown("---")

UUIDS = {
    "es": "d5df4e09-5b0c-44be-a20f-6c60ad9af83d",
    "en": "9cf4c878-78db-428c-8ffb-55ddb610b4d7",
}
MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")

components.iframe(
    f"{MB_HOST}/public/dashboard/{UUIDS[lang]}",
    height=1200,
    scrolling=True,
)
