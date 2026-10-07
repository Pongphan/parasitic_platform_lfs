"""Charts derived from local assets and bounded, real session activity."""
import altair as alt
import pandas as pd
import streamlit as st
from component_ai.registry import model_inventory
from component_theme import CHART_COLORS
from content import quiz_questions

def record_activity(state, report):
    family = report["configuration"]["mode"]
    if family == "keras":
        status = "Failed" if not report.get("predictions") else "Partial" if report.get("errors") else "Completed"
        objects = 0  # A classified crop is not an object-detection count.
    else:
        status, objects = "Completed", len(report.get("detections", []))
    event = {"Time": report["created_at"], "Family": family, "Status": status, "Objects": objects}
    state["analysis_activity"] = [*state.get("analysis_activity", []), event][-200:]

def render_collection_charts(entries):
    with st.container(border=True):
        st.subheader("Practice coverage")
        st.caption("Question availability by group; this describes the collection, not your exam results")
        rows = [{"Atlas entry": e["name"], "Group": e["group"], "Questions": len(quiz_questions(e["id"]))} for e in entries]
        if rows:
            details = pd.DataFrame(rows)
            grouped = details.assign(Covered=details["Questions"] > 0).groupby("Group", as_index=False).agg(
                Entries=("Atlas entry", "size"), Covered=("Covered", "sum"), Questions=("Questions", "sum")
            )
            covered = int((details["Questions"] > 0).sum())
            st.write(f"**{covered} of {len(details)} Atlas entries** have practice questions · **{int(details['Questions'].sum())} questions** in total")
            chart = alt.Chart(grouped).mark_bar(cornerRadiusEnd=4, size=24).encode(
                y=alt.Y("Group:N", title=None, sort="-x"),
                x=alt.X("Questions:Q", axis=alt.Axis(tickMinStep=1)),
                color=alt.value(CHART_COLORS[0]),
                tooltip=["Group", "Questions", alt.Tooltip("Covered:Q", title="Entries with questions"), alt.Tooltip("Entries:Q", title="All entries")],
            ).properties(height=max(150, 34 * len(grouped)))
            st.altair_chart(chart, width="stretch")
            with st.expander("Find practice coverage for an entry"):
                query = st.text_input("Search entry or group", key="home_practice_search", placeholder="For example, Giardia or blood parasites")
                term = query.strip().casefold()
                filtered = details[details.apply(lambda row: term in row["Atlas entry"].casefold() or term in row["Group"].casefold(), axis=1)] if term else details
                if filtered.empty:
                    st.info("No Atlas entries match this search.")
                else:
                    st.caption(f"{len(filtered)} matching entries")
                    st.dataframe(filtered, hide_index=True, width="stretch", height=min(390, 36 * len(filtered) + 38), column_config={"Questions": st.column_config.NumberColumn(format="%d")})
        else:
            st.info("No Atlas entries are available yet.")
    with st.container(border=True):
        st.subheader("Classifier collection")
        st.caption("Local file sizes and contract availability; size is not accuracy")
        rows = [{"Model": item["path"].stem.replace("img_classified_", ""), "Size (MiB)": round(item["path"].stat().st_size / 2**20, 2), "Contract": "Ready" if item["error"] is None else "Invalid"} for item in model_inventory()]
        if rows:
            chart = alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusEnd=4).encode(
                y=alt.Y("Model:N", title=None, sort="-x"), x=alt.X("Size (MiB):Q"),
                color=alt.Color("Contract:N", scale=alt.Scale(domain=["Ready", "Invalid"], range=[CHART_COLORS[2], CHART_COLORS[1]])),
                tooltip=["Model", "Size (MiB)", "Contract"],
            ).properties(height=280)
            st.altair_chart(chart, width="stretch")
        else:
            st.info("No classifier files are available in component_ai/keras/.")

def render_activity():
    st.subheader("This session in the laboratory")
    st.caption("Real analysis runs in this browser session, up to the latest 200. Cleared when the session ends; no simulated usage or accuracy data.")
    activity = st.session_state.get("analysis_activity", [])
    if not activity:
        st.info("Run an analysis in Parasite Detector to populate the activity charts.")
        return
    frame = pd.DataFrame(activity)
    with st.container(horizontal=True):
        st.metric("Analysis runs", len(frame), border=True)
        st.metric("Runs with usable results", int((frame["Status"] != "Failed").sum()), border=True)
        st.metric("Objects detected · YOLO / RCNN", int(frame["Objects"].sum()), border=True)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.caption("Analysis runs by model family and outcome")
        st.altair_chart(alt.Chart(frame).mark_bar().encode(
            x=alt.X("Family:N", title="Model family"), y=alt.Y("count():Q", title="Runs", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Status:N", scale=alt.Scale(domain=["Completed", "Partial", "Failed"], range=[CHART_COLORS[0], CHART_COLORS[2], CHART_COLORS[1]])),
            tooltip=["Family", "Status", alt.Tooltip("count():Q", title="Runs")],
        ).properties(height=210), width="stretch")
    with right, st.container(border=True):
        frame["Minute"] = pd.to_datetime(frame["Time"], utc=True).dt.floor("min")
        timeline = frame.groupby("Minute", as_index=False).size().rename(columns={"size":"Runs"})
        st.caption("Activity timeline · UTC · runs per active minute")
        st.altair_chart(alt.Chart(timeline).mark_bar(color=CHART_COLORS[0], size=12).encode(
            x=alt.X("Minute:T", scale=alt.Scale(type="utc"), axis=alt.Axis(format="%H:%M")),
            y=alt.Y("Runs:Q", axis=alt.Axis(tickMinStep=1)), tooltip=[alt.Tooltip("Minute:T", format="%Y-%m-%d %H:%M UTC"), "Runs"],
        ).properties(height=210), width="stretch")
