import hashlib
import json
import streamlit as st
from component_layout import hero
from content import atlas_entries, quiz_questions, grade
from workspace import get_workspace

def submit_quiz(attempt_key, questions, widget_keys):
    answers = [st.session_state.get(key) for key in widget_keys]
    missing = [str(index + 1) for index, answer in enumerate(answers) if answer is None]
    if missing:
        st.session_state["exam_error"] = (
            f"Answered {len(answers) - len(missing)} / {len(answers)}. "
            "Answer these questions before submitting: " + ", ".join(missing) + "."
        )
        return
    try:
        correct = grade(questions, answers)
    except ValueError as exc:
        st.session_state["exam_error"] = str(exc)
    else:
        st.session_state.exam_attempts[attempt_key] = {"answers": answers, "correct": correct}
        # Legacy species practice feeds the same adaptive learning history.
        from learning import question_pool, start_quiz, submit_active
        ws = get_workspace(st.session_state)
        species_id = attempt_key.split(":")[0]
        selected = [q for q in question_pool(atlas_entries()) if q["species_id"] == species_id]
        saved_active = ws["active_quiz"]
        start_quiz(ws, selected)
        submit_active(ws, answers, [None]*len(answers))
        ws["active_quiz"] = saved_active
        st.session_state.pop("exam_error", None)

def retry_quiz(attempt_key):
    st.session_state.exam_attempts.pop(attempt_key, None)
    for key in list(st.session_state):
        if key.startswith(f"answer_{attempt_key}_"):
            del st.session_state[key]
    st.session_state.exam_round += 1

hero("Learn by doing", "Examination", "Build confidence in the essentials. Choose a species, answer each question, then review the reasoning behind every answer.")
entries = [e for e in atlas_entries() if quiz_questions(e["id"])]
if st.session_state.get("requested_exam_species"):
    st.session_state["practice_mode"] = "Species practice"
practice_mode = st.segmented_control("Practice mode", ["Species practice", "Mixed and adaptive"],
                                     default="Species practice", key="practice_mode", persist_state="session")
if practice_mode == "Mixed and adaptive":
    from component_layout.learning import render_adaptive
    render_adaptive(entries)
elif not entries:
    st.info("No quizzes are available yet.")
else:
    options = [e["id"] for e in entries]
    requested = st.session_state.pop("requested_exam_species", None)
    if requested in options:
        st.session_state["exam_species"] = requested
    species = st.selectbox("Choose a species", options, format_func=lambda x: next(e["name"] for e in entries if e["id"] == x), key="exam_species", persist_state="session")
    questions = quiz_questions(species)
    completed = sum(1 for key in st.session_state.exam_attempts if key.split(":")[0] in options)
    st.caption(f"Learning record · {completed} completed quiz revisions in this session")
    revision = hashlib.sha256(json.dumps(questions, sort_keys=True).encode()).hexdigest()[:12]
    attempt_key = f"{species}:{revision}"
    previous = st.session_state.exam_attempts.get(attempt_key)
    st.caption(f"{len(questions)} questions · Untimed practice · Progress stays in this browser session")
    if st.button("Review this species in the Atlas", icon=":material/menu_book:"):
        st.session_state["requested_atlas_species"] = species
        st.switch_page("pages/atlas.py")
    if previous is None:
        with st.form(f"quiz_{attempt_key}_{st.session_state.exam_round}"):
            widget_keys = []
            for index, question in enumerate(questions, 1):
                widget_key = f"answer_{attempt_key}_{st.session_state.exam_round}_{question['id']}"
                widget_keys.append(widget_key)
                st.radio(f"{index}. {question['question']}", list(range(len(question["options"]))), format_func=lambda i, q=question: q["options"][i], index=None, key=widget_key, persist_state="session")
            st.form_submit_button("Submit answers", type="primary", on_click=submit_quiz, args=(attempt_key, questions, widget_keys))
        if error := st.session_state.pop("exam_error", None):
            st.warning(error)
    else:
        score = sum(previous["correct"])
        st.metric("Your score", f"{score} / {len(questions)}")
        st.progress(score / len(questions))
        st.subheader("Review your answers")
        if score < len(questions):
            st.info("Use Review this species in the Atlas to revisit identification notes, then try again. Your current answers remain saved during navigation.")
        for index, (q, answer, correct) in enumerate(zip(questions, previous["answers"], previous["correct"]), 1):
            with st.container(border=True):
                st.markdown(f"**{index}. {q['question']}**")
                (st.success if correct else st.error)("Correct" if correct else "Review this answer")
                st.write(f"Your answer: {q['options'][answer]}")
                if not correct:
                    st.write(f"Correct answer: {q['options'][q['correct_answer']]}")
                st.write(q["explanation"])
        report = {"species": species, "quiz_revision": revision, "score": score, "total": len(questions), **previous}
        st.download_button("Download practice result", json.dumps(report, indent=2), file_name=f"{species}_practice.json", mime="application/json")
        st.button("Try again", icon=":material/refresh:", on_click=retry_quiz, args=(attempt_key,))
