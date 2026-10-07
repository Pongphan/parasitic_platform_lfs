from collections import Counter
import altair as alt
import pandas as pd
import streamlit as st
from component_layout import hero
from component_theme import CHART_COLORS
from component_ai.registry import discover_models
from component_ai.images import discover_samples
from content import ROOT, atlas_entries, quiz_questions
from component_layout.dashboard import render_collection_charts, render_activity

hero("A living laboratory of knowledge", "Explore. Observe. Practice.", "Find a parasite reference, examine a microscopy image, or test your knowledge. Choose a task to get started.")

# Render the three routes before loading collection statistics or model inventory.
with st.container(horizontal=True, gap="small", key="home_tasks"):
    for task, title, description, action, icon, page, action_key in [
        ("atlas", "Explore the Atlas", "Find morphology, life cycles, diagnostic notes, and comparison guides.", "Open Atlas", ":material/menu_book:", "pages/atlas.py", "home_atlas_action"),
        ("detector", "Examine an image", "Upload a microscopy image or try a sample, then review AI findings.", "Analyze image", ":material/biotech:", "pages/detector.py", "home_detector_action"),
        ("practice", "Build your knowledge", "Practice a topic, mix questions, or revisit areas that need attention.", "Start practice", ":material/quiz:", "pages/examination.py", "home_practice_action"),
    ]:
        with st.container(border=True, width=360, height="stretch", key=f"home_task_{task}"):
            st.subheader(title)
            st.write(description)
            if st.button(action, icon=icon, type="primary" if task == "atlas" else "secondary", key=action_key, width="stretch"):
                st.switch_page(page)

entries = atlas_entries()
questions = sum(len(quiz_questions(e["id"])) for e in entries)
st.caption("Available in this collection")
with st.container(horizontal=True, key="home_collection_metrics"):
    for title, value in [("Atlas entries", len(entries)), ("Practice questions", questions), ("Keras models", len(discover_models())), ("Microscopy samples", len(discover_samples(ROOT / "component_aiimage")))]:
        st.metric(title, f"{value:02d}", border=True)

with st.expander("Collection overview and practice coverage"):
    st.subheader("Inside the Atlas")
    st.caption("Reference entries by group, including species, species groups, and artifacts")
    counts = Counter(e["group"] for e in entries)
    frame = pd.DataFrame([{"Group": k, "Entries": v} for k, v in counts.items()], columns=["Group", "Entries"])
    if not frame.empty:
        chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=6, size=24).encode(
            x=alt.X("Entries:Q", axis=alt.Axis(tickMinStep=1), title="Atlas entries"),
            y=alt.Y("Group:N", title=None),
            color=alt.Color("Group:N", scale=alt.Scale(range=CHART_COLORS), legend=None),
            tooltip=["Group", "Entries"],
        ).properties(height=max(150, 34 * len(frame)))
        st.altair_chart(chart, width="stretch")
    st.caption("Calculated from local content. These counts are not disease prevalence or model performance.")
    render_collection_charts(entries)

with st.expander("Detection workbench availability"):
    from component_ai.detection import AUTO_MODELS, auto_detector_contract, model_display_name
    with st.container(horizontal=True):
        for name in AUTO_MODELS:
            with st.container(border=True, width=280):
                st.markdown(f"**{model_display_name(name)}**")
                try:
                    _, _, checkpoint = auto_detector_contract(name)
                    st.caption("Checkpoint installed" if checkpoint.is_file() else "Checkpoint needed")
                except (ValueError, KeyError, OSError):
                    st.caption("Configuration needs attention")
    st.caption("File availability does not establish model accuracy. Open Parasite Detector for setup details and analysis.")
with st.expander("Guided microscopy learning workflow"):
    st.markdown("**1. Observe** — Open a sample in Parasite Detector. Choose Classify selected region and position a target in the center box with pan and zoom.")
    st.markdown("**2. Describe** — Record visible shape, shell or boundary, internal structures, and image quality before viewing a model score.")
    st.markdown("**3. Compare** — Use the Atlas morphology comparison and annotated illustrations to review candidate identities and identification limits.")
    st.markdown("**4. Review** — Compare model findings with your observations, export the analysis, and practice the relevant species quiz.")
    st.caption("Learning workflow only. Image pixels do not establish physical size without microscope calibration.")
    if st.button("Start with a microscopy image", icon=":material/biotech:"):
        st.switch_page("pages/detector.py")
with st.expander("Your analysis activity"):
    render_activity()
