"""Shared application shell: rendered once by the entry point on every page."""
from html import escape
import streamlit as st

def render_header():
    st.html('<header class="brand"><div class="brand-mark" aria-hidden="true">🔬</div><div><small>Observe · understand · discover</small><h1>Parasitic Platform</h1></div><span class="edition">2027 EDITION</span></header>')

def render_navigation(routes, current):
    with st.container(horizontal=True, key="card_nav"):
        for index, page in enumerate(routes):
            if st.button(page.title, icon=page.icon, key=f"nav_{index}", width="stretch", type="primary" if page.url_path == current.url_path else "secondary"):
                st.switch_page(page)

def hero(kicker, title, description, *, compact=None):
    if compact is None:
        compact = bool(st.session_state.get("_active_route"))
    css_class = "hero hero--compact" if compact else "hero"
    st.html(f'<section class="{css_class}"><span class="eyebrow">{escape(kicker)}</span><h2>{escape(title)}</h2><p>{escape(description)}</p></section>')

def render_footer():
    st.html('<footer class="footer"><span>Parasitic Platform / 2027 · A closer look at parasitology.</span><span>Education &amp; research · AI findings require qualified review.</span></footer>')
