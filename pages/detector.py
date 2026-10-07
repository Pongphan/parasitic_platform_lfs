from component_layout import hero
from component_layout.detector import render_detector
import streamlit as st

hero("AI-assisted microscopy", "Parasite Detector", "Choose an image, inspect a region, and compare model findings. Keep morphology and specimen context at the center of your interpretation.")
if requested := st.session_state.pop("requested_review_analysis", None):
    for suffix in ("_states", "_labels", "_object", "_advance_to", "_reveal_review",
                   "_restore_filtered_selection", "_review_notice"):
        st.session_state.pop(f"history_{requested}{suffix}", None)
    st.session_state.update(detector_workspace="Advanced workspace", workspace_tool="Session workspace",
                            history_record=requested, history_status=["completed", "partial", "failed"],
                            expanded_review=requested)
workspace_mode = st.radio("Detector workspace", ["Single image", "Advanced workspace"], horizontal=True,
                          key="detector_workspace", persist_state="session")
if workspace_mode == "Single image":
    render_detector()
else:
    from component_layout.workbench import render_workbench
    render_workbench()
