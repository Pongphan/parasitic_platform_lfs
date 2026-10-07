import math
import streamlit as st
from component_layout import hero
from content import atlas_entries, export_atlas, filter_atlas, local_asset, localized_entry
from component_layout.learning import render_learning_library, render_entry_learning


def open_entry(species_id):
    st.session_state["requested_atlas_species"] = species_id


def reset_atlas_filters():
    st.session_state.update(atlas_search="", atlas_group="All groups", atlas_route="All routes",
                            atlas_clinical="All clinical contexts", atlas_index_page=1)


def bullets(values):
    for value in values:
        st.markdown(f"- {value}")


hero("The reference collection", "Parasite Atlas", "Study diagnostic stages, compare look-alikes and connect model findings to their reference material.")
entries = atlas_entries()
by_id = {entry["id"]: entry for entry in entries}
render_learning_library(entries)
requested = st.session_state.pop("requested_atlas_species", None)
if requested in by_id:
    # Detector and Examination links clear restrictive index filters.
    st.session_state.update(atlas_search="", atlas_group="All groups", atlas_route="All routes",
                            atlas_clinical="All clinical contexts", atlas_species=requested, atlas_index_page=1)
st.caption(f"{len(entries)} species and reference groups · Intestinal, blood and tissue-associated parasites · Source-linked learning")
query = st.text_input("Search species", placeholder="Name, synonym, morphology, specimen or model label…", key="atlas_search")
groups, routes, contexts = st.columns(3)
group = groups.selectbox("Taxonomic group", ["All groups"] + sorted({e["group"] for e in entries}), key="atlas_group")
route = routes.selectbox("Transmission", ["All routes"] + sorted({r for e in entries for r in e["transmission"]["types"]}), key="atlas_route")
clinical = contexts.selectbox("Clinical significance", ["All clinical contexts"] + sorted({t for e in entries for t in e["clinical_tags"]}), key="atlas_clinical")
matches = filter_atlas(entries, query, group, route, clinical)
if query or group != "All groups" or route != "All routes" or clinical != "All clinical contexts":
    st.button("Clear all filters", icon=":material/filter_alt_off:", key="atlas_clear_filters", on_click=reset_atlas_filters)
with st.expander("Compare morphology side by side"):
    compare = st.multiselect("Species to compare", list(by_id), format_func=lambda value: by_id[value]["name"],
                             max_selections=3, key="atlas_compare", persist_state="session")
    compared = [by_id[value] for value in compare]
    if compared:
        st.caption("Schematics are educational illustrations, not microscopy images. Displayed image sizes are not a shared physical scale; compare stated µm ranges, not screen size.")
        for column, item in zip(st.columns(len(compared)), compared):
            with column:
                st.markdown(f"**{item['name']}**")
                st.caption(item['common_name'])
                if item['images']:
                    illustration = item['images'][0]
                    st.image(str(local_asset(item['folder'], illustration['file'])), width="stretch", caption=illustration['caption'])
                else:
                    st.caption("No local schematic. Open the reference gallery in this entry.")
        for title, field in [("Diagnostic specimen", "specimen"), ("Morphology", "morphology"),
                             ("Look-alikes and identification limits", "differential_diagnosis")]:
            st.markdown(f"**{title}**")
            for column, item in zip(st.columns(len(compared)), compared):
                with column:
                    st.caption(item['name'])
                    if isinstance(item[field], list):
                        bullets(item[field])
                    else:
                        st.write(item[field])
        with st.expander("Detailed comparison table"):
            st.dataframe([{"Species": e["name"], "Group": e["group"], "Diagnostic specimen": e["specimen"],
                           "Identification notes": " • ".join(e["morphology"]),
                           "Common confusion": " • ".join(e["differential_diagnosis"]),
                           "Model labels": ", ".join(e["classifier_labels"]) or "Reference only"}
                          for e in compared], hide_index=True, width="stretch")
        st.download_button("Download comparison with sources", export_atlas(compared), file_name="parasite_comparison.json", mime="application/json")
    else:
        st.caption("Choose up to three entries to compare specimen, morphology, look-alikes and model coverage.")
if not matches:
    st.info("No species match your search. Try a broader name or reset the filters.")
else:
    st.caption(f"Showing {len(matches)} of {len(entries)} entries")
    with st.expander("Browse reference cards", expanded=False):
        page_count = max(1, math.ceil(len(matches) / 8))
        if st.session_state.get("atlas_index_page", 1) > page_count:
            st.session_state["atlas_index_page"] = 1
        page = st.number_input("Index page", min_value=1, max_value=page_count, step=1, key="atlas_index_page")
        with st.container(horizontal=True, gap="medium"):
            for card in matches[(page - 1) * 8:page * 8]:
                with st.container(border=True, width=290):
                    st.caption(card["group"] + " · " + card["entry_type"].replace("_", " "))
                    st.markdown(f"**{card['name']}**")
                    st.write(card["common_name"])
                    st.caption(" · ".join(card["clinical_tags"]))
                    st.button("Open reference", key=f"atlas_open_{card['id']}", on_click=open_entry, args=(card["id"],))
    options = [e["id"] for e in matches]
    if st.session_state.get("atlas_species") not in options:
        st.session_state["atlas_species"] = options[0]
    selected = st.selectbox("Explore a species", options, format_func=lambda value: by_id[value]["name"], key="atlas_species")
    original = by_id[selected]
    render_entry_learning(original, entries)
    languages = ["en"] + sorted(k for k, value in original["translations"].items() if k != "en" and value)
    language = st.selectbox("Reference language", languages, format_func=lambda x: {"en": "English", "th": "ไทย"}.get(x, x)) if len(languages) > 1 else "en"
    entry = localized_entry(original, language)
    if language != "en":
        st.caption("Fields without a translation are shown in English.")
    elif len(languages) == 1:
        st.caption("English reference; translated content is not available for this entry.")
    with st.container(border=True):
        st.subheader(entry["name"])
        st.caption(f"{entry['common_name']} · {entry['group']} · {entry['entry_type'].replace('_', ' ')}")
        st.write(entry["description"])
        overview, cycle, clinical_tab, diagnostic, model, sources = st.tabs([
            "Morphology & images", "Life cycle & hosts", "Clinical context", "Diagnosis & look-alikes", "Model & annotation", "Sources"])
        with overview:
            st.markdown("**Taxonomic lineage**")
            st.write(entry["taxonomy"]["lineage"])
            if entry["aliases"]:
                st.caption("Synonyms / search names: " + " · ".join(entry["aliases"]))
            st.markdown("**Diagnostic-stage morphology**")
            bullets(entry["morphology"])
            st.markdown("**Schematic morphology**")
            for illustration in entry["images"]:
                st.image(str(local_asset(entry["folder"], illustration["file"])),
                         caption=illustration["caption"], width=800 if illustration.get("kind") == "schematic" else 420)
            for reference in entry["reference_images"]:
                st.link_button("Open reference microscopy gallery", reference["url"], icon=":material/open_in_new:")
                st.caption(reference["caption"] + " " + reference["rights"])
            st.caption("Size ranges describe structures in µm, not crop pixels. Local schematics are educational illustrations, not microscopy ground truth.")
        with cycle:
            st.markdown("**Transmission**")
            st.write(" · ".join(entry["transmission"]["types"]))
            for i, step in enumerate(entry["life_cycle"], 1):
                st.markdown(f"**{i:02d} / {step['stage']}**")
                st.write(step["detail"])
            st.markdown("**Definitive, intermediate and reservoir hosts**")
            st.write(entry["hosts"])
        with clinical_tab:
            st.markdown("**Geographic distribution / Thailand and Southeast Asia**")
            st.write(entry["distribution"])
            st.markdown("**Clinical significance**")
            st.write(entry["clinical_significance"])
        with diagnostic:
            st.markdown("**Specimen and diagnostic stages**")
            st.write(entry["specimen"])
            st.markdown("**Methods, stains and microscopy**")
            bullets(entry["diagnostics"])
            st.markdown("**Differential identification and limitations**")
            bullets(entry["differential_diagnosis"])
        with model:
            st.markdown("**Model coverage: " + entry["model_mapping"]["status"] + "**")
            st.write("Configured labels: " + (", ".join(entry["classifier_labels"]) or "None"))
            st.write(entry["model_mapping"]["note"])
            if related := entry["model_mapping"]["related_atlas_id"]:
                st.button("Open related morphology group: " + by_id[related]["name"], on_click=open_entry, args=(related,), key="atlas_related")
                st.caption("A related group is not an exact species-level model match.")
            st.markdown("**Dataset annotation guidance**")
            bullets(entry["annotation_guidance"])
        with sources:
            for source in entry["references"]:
                st.markdown(f"[{source['title']}]({source['url']})")
            st.caption(f"Source compilation: {entry['reviewed_on']}. {entry['review_status']}.")
            st.download_button("Download this reference (JSON)", export_atlas([original]), file_name=f"{selected}_reference.json", mime="application/json")
    if st.button("Practice this species", icon=":material/quiz:", type="primary", key="atlas_practice_action"):
        st.session_state["requested_exam_species"] = selected
        st.switch_page("pages/examination.py")
with st.expander("Export the reference collection"):
    st.download_button("Download filtered Atlas (JSON)", export_atlas(matches), file_name="parasite_atlas.json", mime="application/json")
