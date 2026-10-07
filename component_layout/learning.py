"""Native adaptive quizzes, bookmarks and source-grounded learning pathways."""
from collections import Counter
import streamlit as st
from workspace import get_workspace, json_bytes
from learning import question_pool, select_questions, start_quiz, submit_active, related_entries


def capture_answer(quiz, index, key, field):
    quiz[field][index] = st.session_state.get(key)


def move_to_question(key, index):
    st.session_state[key] = index


def render_adaptive(entries):
    ws = get_workspace(st.session_state)
    st.subheader("Mixed and adaptive practice")
    st.caption("Selection prioritizes recent incorrect answers, then least-practiced questions. This describes session practice, not validated competency.")
    groups = st.multiselect("Practice taxonomic groups", sorted({e['group'] for e in entries}), key="practice_groups", persist_state="session")
    missed = st.checkbox("Practice missed questions only", key="practice_missed", persist_state="session")
    ratings = st.checkbox("Include optional confidence ratings", key="practice_ratings", persist_state="session")
    pool = question_pool(entries, groups)
    candidates = select_questions(pool, ws['question_history'], len(pool), missed)
    available = len(candidates)
    maximum = max(1, available)
    st.session_state['practice_count'] = min(maximum, max(1, st.session_state.get('practice_count', min(10, maximum))))
    count = st.number_input("Questions in the next quiz", min_value=1, max_value=maximum,
                            key="practice_count", persist_state="session", disabled=not available)
    st.caption(f"{available} questions available for this selection. Leave groups empty to practice the whole collection.")
    if not available:
        st.info("No questions match this selection. Turn off missed-only practice or choose different groups.")
    active = ws['active_quiz']
    replace = True
    if active and not active['submitted']:
        replace = st.checkbox("Replace my unfinished practice quiz", key="replace_active_quiz")
    if st.button("Start practice quiz", disabled=not replace or not available, key="start_adaptive"):
        try:
            start_quiz(ws, candidates[:int(count)])
            st.rerun()
        except ValueError as exc:
            st.info(str(exc))
    quiz = ws['active_quiz']
    if quiz:
        st.caption(f"Active quiz: {len(quiz['questions'])} unique questions. Setup changes affect the next quiz only.")
        if not quiz['submitted']:
            total = len(quiz['questions'])
            unanswered = [index for index, answer in enumerate(quiz['answers']) if answer is None]
            answered = total - len(unanswered)
            st.progress(answered / total, text=f"Answered {answered} / {total}")
            navigator = f"adaptive_nav_{quiz['id']}"
            st.session_state.setdefault(navigator, 0)
            selected = st.selectbox("Question navigator", list(range(total)), key=navigator,
                                    format_func=lambda i: f"Question {i + 1} · {'Unanswered' if quiz['answers'][i] is None else 'Answered'}",
                                    persist_state="session")
            page_size = 5
            start = selected // page_size * page_size
            end = min(start + page_size, total)
            st.caption(f"Page {start // page_size + 1} of {(total + page_size - 1) // page_size} · Questions {start + 1}–{end}")
            with st.container(horizontal=True):
                st.button("Previous questions", key="adaptive_previous", disabled=start == 0,
                          on_click=move_to_question, args=(navigator, max(0, start - page_size)))
                st.button("Next questions", key="adaptive_next", disabled=end == total,
                          on_click=move_to_question, args=(navigator, min(end, total - 1)))
                st.button("Go to first unanswered", key="adaptive_unanswered", disabled=not unanswered,
                          on_click=move_to_question, args=(navigator, unanswered[0] if unanswered else 0))
            for index in range(start, end):
                q = quiz['questions'][index]
                key = f"adaptive_{quiz['id']}_{index}"
                st.session_state.setdefault(key, quiz['answers'][index])
                st.radio(f"{index+1}. {q['question']}", list(range(len(q['options']))),
                         format_func=lambda i, question=q:question['options'][i], index=None, key=key,
                         persist_state="session", on_change=capture_answer, args=(quiz,index,key,'answers'))
                if ratings:
                    rating_key = key + '_confidence'
                    st.session_state.setdefault(rating_key, quiz['confidence'][index])
                    st.selectbox("Your confidence (optional)", ['Low', 'Medium', 'High'], index=None,
                                 key=rating_key, persist_state="session", on_change=capture_answer,
                                 args=(quiz,index,rating_key,'confidence'))
            if st.button("Submit practice quiz", key="submit_adaptive"):
                if unanswered:
                    st.warning("Answer these questions before submitting: " + ", ".join(str(i + 1) for i in unanswered) + ". Use the question navigator or Go to first unanswered.")
                else:
                    try:
                        submit_active(ws, quiz['answers'], quiz['confidence'])
                        st.rerun()
                    except ValueError as exc:
                        st.warning(str(exc))
        else:
            st.metric("Practice score", f"{sum(quiz['correct'])} / {len(quiz['questions'])}")
            for index, (q, answer, correct) in enumerate(zip(quiz['questions'], quiz['answers'], quiz['correct'])):
                with st.container(border=True):
                    st.write(q['question'])
                    (st.success if correct else st.error)("Correct" if correct else "Review this answer")
                    st.write("Your answer: " + q['options'][answer])
                    st.write("Correct answer: " + q['options'][q['correct_answer']])
                    st.write(q['explanation'])
                    if st.button("Open Atlas: " + q['species_name'], key=f"adaptive_atlas_{index}"):
                        st.session_state['requested_atlas_species'] = q['species_id']
                        st.switch_page('pages/atlas.py')
            st.download_button("Download adaptive practice result", json_bytes(quiz), 'adaptive_practice.json')
    if ws['question_history']:
        totals = Counter(r['group'] for r in ws['question_history'])
        correct = Counter(r['group'] for r in ws['question_history'] if r['correct'])
        st.subheader("Topics from your actual attempts")
        st.dataframe([{'Topic': group, 'Answered': count, 'Correct': correct[group], 'Needs review': count-correct[group], 'Correct fraction': correct[group]/count} for group,count in totals.items()], hide_index=True)
        st.caption("Repeated attempts count separately. The most recent 2,000 question attempts are retained.")


def render_learning_library(entries):
    ws = get_workspace(st.session_state)
    by_id = {e['id']: e for e in entries}
    with st.expander("Bookmarks and learning lists"):
        st.caption("Bookmarks and learning lists are saved only in this session. Use Session tools to export a copy before leaving.")
        if ws['bookmarks']:
            chosen = st.selectbox("Bookmarked reference", ws['bookmarks'], format_func=lambda k:by_id[k]['name'])
            if st.button("Open bookmarked reference"):
                st.session_state['requested_atlas_species'] = chosen
                st.rerun()
        else:
            st.caption("Open an entry and bookmark it to start a learning list.")
        grouping = st.selectbox("Group learning list by", ['Taxonomic category', 'Clinical topic'])
        topics = sorted({e['group'] for e in entries} if grouping == 'Taxonomic category' else {tag for e in entries for tag in e.get('clinical_tags', [])})
        topic = st.selectbox("Learning topic", topics)
        choices = [e['id'] for e in entries if e['group'] == topic or topic in e.get('clinical_tags', [])]
        selected = st.multiselect("References in the list", choices, default=choices, format_func=lambda k:by_id[k]['name'], key='learning_selection_'+topic)
        name = st.text_input("Learning list name", value=topic, max_chars=100)
        if st.button("Save learning list", disabled=not name.strip() or not selected):
            if len(ws['learning_lists']) >= 50 and name.strip() not in ws['learning_lists']:
                st.warning("The session supports up to 50 learning lists.")
            else:
                ws['learning_lists'][name.strip()] = list(selected)
                st.success("Learning list saved in this session. Export your session to keep a copy.")
        if ws['learning_lists']:
            selected_list = st.selectbox("Saved learning list", list(ws['learning_lists']))
            for key in ws['learning_lists'][selected_list]:
                if st.button(by_id[key]['name'], key='learning_open_'+key):
                    st.session_state['requested_atlas_species'] = key
                    st.rerun()
            if st.button("Remove selected learning list"):
                del ws['learning_lists'][selected_list]
                st.rerun()


def render_entry_learning(entry, entries):
    ws = get_workspace(st.session_state)
    bookmarked = entry['id'] in ws['bookmarks']
    if st.button("Remove bookmark" if bookmarked else "Bookmark this reference", key='atlas_bookmark',
                 help="Bookmarks are saved only in this session. Use Session tools to export a copy."):
        if bookmarked:
            ws['bookmarks'].remove(entry['id'])
        else:
            ws['bookmarks'].append(entry['id'])
        st.rerun()
    with st.expander("Guided learning pathway"):
        st.markdown("1. Describe structures in **Morphology & images**.\n2. Follow **Life cycle & hosts** to connect stages and transmission.\n3. Compare specimens and look-alikes in **Diagnosis & look-alikes**.\n4. Open the microscopy workbench to review an image.\n5. Return and use **Practice this species** to check recall.")
        st.caption("The pathway connects existing references. It does not imply bundled samples contain this species or the detector recognizes it.")
        if st.button("Open microscopy workbench", key='learning_detector'):
            st.switch_page('pages/detector.py')
    with st.expander("Related references from structured content"):
        for candidate, reasons in related_entries(entry, entries):
            st.caption(' · '.join(reasons))
            if st.button(candidate['name'], key='related_learning_'+candidate['id']):
                st.session_state['requested_atlas_species'] = candidate['id']
                st.rerun()
