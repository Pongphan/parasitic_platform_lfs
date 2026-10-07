"""Run with: streamlit run app.py (from this project directory)."""
import streamlit as st

from component_layout import render_header, render_navigation, render_footer
from component_theme import apply_theme
from component_layout.session_tools import render_session_tools

st.set_page_config(page_title="Parasitic Platform", page_icon="🔬", layout="wide", initial_sidebar_state="collapsed")
apply_theme()
st.session_state.setdefault("detector_result", None)
st.session_state.setdefault("exam_attempts", {})
st.session_state.setdefault("exam_round", 0)

routes = [
    st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("pages/atlas.py", title="Parasite Atlas", icon=":material/menu_book:", url_path="atlas"),
    st.Page("pages/detector.py", title="Parasite Detector", icon=":material/biotech:", url_path="detector"),
    st.Page("pages/examination.py", title="Examination", icon=":material/quiz:", url_path="examination"),
    st.Page("pages/about.py", title="About", icon=":material/info:", url_path="about"),
]
current = st.navigation(routes, position="hidden")
st.session_state["_active_route"] = current.url_path
render_header()
render_navigation(routes, current)
# Render here after the page runs so status reflects edits made in this rerun.
session_tools_slot = st.container(key="shared_session_tools")
current.run()
with session_tools_slot:
    render_session_tools()
render_footer()
