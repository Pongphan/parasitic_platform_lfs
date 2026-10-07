"""Current workspace guide with the complete 2026 project narrative retained."""
import streamlit as st
from component_layout import hero


hero(
    "The project",
    "About Parasitic Platform",
    "A shared workspace for parasite references, microscopy review, and active learning.",
)

st.subheader("What you can do here")
with st.container(border=True):
    st.markdown(
        "**Parasite Atlas** — Search reference entries, compare morphology, and save topics to revisit.\n\n"
        "**Parasite Detector** — Review one image or a batch, compare model findings, correct objects, "
        "and export reports or annotations.\n\n"
        "**Examination** — Choose a topic, mix questions, or practice areas highlighted by your previous attempts.\n\n"
        "**Home** — Start a task and inspect collection coverage or activity from this session."
    )

with st.container(horizontal=True, gap="small"):
    with st.container(border=True, width=530):
        st.subheader("A simple learning workflow")
        st.write("Read an Atlas entry, examine a microscopy image, then use practice questions to check your understanding.")
        st.caption("For laboratory staff, researchers, educators, students, and project teams.")
    with st.container(border=True, width=530):
        st.subheader("Models and session data")
        st.write("Image analysis uses locally installed Keras, YOLO, or Faster R-CNN models. Model availability and setup details are shown in Detector.")
        st.caption("Export a session archive to keep your work. Source images are optional, and reviewed annotations do not retrain the models.")

st.subheader("Project boundaries")
st.write(
    "This workspace supports education and research. AI scores require qualified review and do not replace "
    "institutional SOPs, validated clinical diagnostic pathways, regulatory approval, or professional judgment."
)
st.caption("Atlas coverage does not expand a model's trained classes. Supplied models have no bundled independent clinical validation or calibration report.")

with st.expander("2026 project history and research blueprint"):
    st.caption("The original project narrative is retained below. The research branch browser and study blueprint generator belong to the 2026 edition.")
    st.write("A practical digital workspace for parasitology education, research planning, and AI-assisted microscopy review. This edition brings reference knowledge, image review, and active practice into one consistent interface.")
    st.subheader("Project at a glance")
    with st.container(horizontal=True, gap="small"):
        with st.container(border=True, width=350):
            st.markdown("### Purpose")
            st.write(
                "Help parasitology teams move from organism knowledge to research design and "
                "microscopy-assisted analysis without switching between disconnected tools."
            )
        with st.container(border=True, width=350):
            st.markdown("### Primary users")
            st.write(
                "Laboratory staff, parasitology researchers, educators, students, and project teams "
                "preparing SOPs, study protocols, image datasets, or diagnostic reports."
            )
        with st.container(border=True, width=350):
            st.markdown("### Current focus")
            st.write(
                "Human parasite reference content, active practice, and AI-supported "
                "microscopy classification using selectable trained models."
            )

    st.subheader("How the modules fit together")
    with st.container(border=True):
        st.markdown(
            "**1. Parasite Atlas — Human Parasite in the 2026 edition**\n\n"
            "Use this as the knowledge base: parasite profiles, clinical context, diagnostic notes, "
            "morphology cues, common pitfalls, and prevention/control points.\n\n"
            "**2. Parasitology Research — 2026 edition**\n\n"
            "Use this to turn a topic into a structured project: research questions, methods, "
            "study designs, outputs, ethics/quality notes, and a downloadable study blueprint. "
            "The research branch browser and blueprint generator are available in the 2026 "
            "project; they are not included in this edition.\n\n"
            "**3. Parasite Detector — Parasitic Vision in the 2026 edition**\n\n"
            "Use this for AI-assisted microscopy image review: choose or upload images, position "
            "the region of interest, run selected models, and compare predictions.\n\n"
            "**4. Examination**\n\n"
            "Use this to practice species-specific or mixed questions, review explained answers, "
            "and revisit topics through adaptive practice.\n\n"
            "**5. About Project**\n\n"
            "Use this page to understand the project scope, workflow, readiness, limitations, and roadmap."
        )

    st.subheader("Recommended workflow")
    with st.container(horizontal=True, gap="small"):
        with st.container(border=True, width=530):
            st.markdown("### Daily lab or teaching use")
            st.write(
                "Start in Parasite Atlas for organism context and diagnostic reminders. Move to "
                "Parasite Detector when image review or model-supported ROI classification is needed. "
                "Use Examination to reinforce the relevant topics."
            )
        with st.container(border=True, width=530):
            st.markdown("### Research project use")
            st.write(
                "In the 2026 edition, start in Parasitology Research, select a branch, and generate "
                "a blueprint. Link the protocol to atlas content and imaging outputs where relevant. "
                "In this edition, use the Detector workspace to review images, compare analyses, "
                "and export findings or reviewed annotations for your project."
            )

    st.subheader("What is ready now")
    with st.container(border=True):
        st.markdown(
            "**Ready for use in this edition**\n\n"
            "- Module navigation with no sidebar dependency\n"
            "- Human parasite educational/reference workspace\n"
            "- Microscopy image viewer with auto viewport sizing\n"
            "- Model selection and multi-model prediction summary\n"
            "- Species-specific and adaptive practice\n"
            "- Batch analysis, object review, comparison, and report exports\n\n"
            "**Requires local project data/models**\n\n"
            "- Trained Keras models in `component_ai/keras/`\n"
            "- Detection checkpoints in `component_ai/yolo/weights/` and `component_ai/rcnn/weights/`\n"
            "- Image examples in `component_aiimage/`\n"
            "- Local SOPs, citations, or team-specific reporting templates"
        )

    st.subheader("Project boundaries")
    st.warning(
        "This platform supports education, research planning, laboratory workflow organization, "
        "and AI-assisted review. It does not replace institutional SOPs, validated clinical "
        "diagnostic pathways, regulatory approval, or expert professional judgment."
    )

    st.subheader("Roadmap")
    with st.container(border=True):
        st.markdown(
            "**Phase 1: Foundation**\n\n"
            "- Standardize navigation, theme, and module layout\n"
            "- Build parasite atlas, research planning, and image review pages\n\n"
            "**Phase 2: Practical readiness**\n\n"
            "- Improve page clarity and workflow guidance\n"
            "- Add downloadable research outputs and cleaner project documentation\n"
            "- Strengthen microscopy model comparison and reporting\n\n"
            "**Phase 3: Research-grade expansion**\n\n"
            "- Add curated citations and SOP attachments\n"
            "- Add dataset/model documentation and validation summaries\n"
            "- Prepare stable deployment and team-specific configuration"
        )
