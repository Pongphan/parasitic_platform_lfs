"""Centralized CSS and chart tokens; native widget theme lives in theme.toml."""
from pathlib import Path
import streamlit as st

TEAL = "#20665C"
CHART_COLORS = [TEAL, "#BD715D", "#7C81A8", "#809D69"]

def apply_theme():
    st.html(Path(__file__).with_name("styles.css"))
