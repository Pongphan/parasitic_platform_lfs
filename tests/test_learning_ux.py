"""Behavior checks for Atlas recovery and paginated practice state."""
from copy import deepcopy

from test_app import app, explicit_navigation_test_runtime
from content import quiz_questions
from session_archive import export_session, import_session


def adaptive(count=12):
    at = app().switch_page('pages/examination.py').run()
    at.segmented_control(key='practice_mode').set_value('Mixed and adaptive').run()
    at.number_input(key='practice_count').set_value(count).run()
    at.button(key='start_adaptive').click().run()
    assert not at.exception
    return at


def test_atlas_clear_filters_recovers_empty_results_and_preserves_comparison():
    at = app().switch_page('pages/atlas.py').run()
    compared = ['giardia_duodenalis', 'ascaris_lumbricoides']
    at.multiselect(key='atlas_compare').set_value(compared).run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 2
    assert any('not a shared physical scale' in item.value for item in at.caption)
    # Two comparison schematics plus the currently selected reference image.
    assert len(at.image) >= 3
    at.text_input(key='atlas_search').set_value('no matching reference')
    at.selectbox(key='atlas_group').set_value('Cestodes')
    at.selectbox(key='atlas_route').set_value('Vector-borne')
    at.selectbox(key='atlas_clinical').set_value('Anemia').run()
    assert any('No species match' in item.value for item in at.info)
    at.button(key='atlas_clear_filters').click().run()
    assert not at.exception
    assert at.text_input(key='atlas_search').value == ''
    assert at.selectbox(key='atlas_group').value == 'All groups'
    assert at.selectbox(key='atlas_route').value == 'All routes'
    assert at.selectbox(key='atlas_clinical').value == 'All clinical contexts'
    assert at.multiselect(key='atlas_compare').value == compared
    assert at.selectbox(key='atlas_species').value


def test_adaptive_pages_preserve_answers_confidence_and_restore_from_archive():
    at = adaptive()
    quiz = at.session_state['workspace']['active_quiz']
    snapshot = deepcopy(quiz['questions'])
    prefix = f"adaptive_{quiz['id']}_"
    assert len(at.radio) == 5
    at.checkbox(key='practice_ratings').set_value(True).run()
    at.radio(key=prefix + '0').set_value(quiz['questions'][0]['correct_answer']).run()
    at.selectbox(key=prefix + '0_confidence').set_value('High').run()
    at.button(key='adaptive_next').click().run()
    assert at.radio[0].key == prefix + '5'
    at.radio(key=prefix + '5').set_value(quiz['questions'][5]['correct_answer']).run()
    at.button(key='adaptive_next').click().run()
    assert len(at.radio) == 2
    at.button(key='submit_adaptive').click().run()
    assert any('2, 3, 4, 5, 7, 8, 9, 10, 11, 12' in item.value for item in at.warning)
    assert not at.session_state['workspace']['question_history']
    at.button(key='adaptive_unanswered').click().run()
    assert at.selectbox(key=f"adaptive_nav_{quiz['id']}").value == 1
    assert at.radio(key=prefix + '0').value == quiz['questions'][0]['correct_answer']
    at.switch_page('pages/atlas.py').run()
    at.switch_page('pages/examination.py').run()
    assert not at.exception
    assert at.selectbox(key=prefix + '0_confidence').value == 'High'
    assert at.session_state['workspace']['active_quiz']['questions'] == snapshot

    restored = import_session(export_session(at.session_state['workspace']))
    fresh = app()
    fresh.session_state['workspace'] = restored
    fresh.switch_page('pages/examination.py').run()
    fresh.segmented_control(key='practice_mode').set_value('Mixed and adaptive').run()
    fresh.checkbox(key='practice_ratings').set_value(True).run()
    assert not fresh.exception
    assert fresh.radio(key=prefix + '0').value == quiz['questions'][0]['correct_answer']
    assert fresh.selectbox(key=prefix + '0_confidence').value == 'High'
    assert fresh.session_state['workspace']['active_quiz']['answers'][5] == quiz['questions'][5]['correct_answer']
    assert fresh.get('progress')[0].proto.text == 'Answered 2 / 12'


def test_paginated_quiz_submits_all_pages_once():
    at = adaptive()
    quiz = at.session_state['workspace']['active_quiz']
    prefix = f"adaptive_{quiz['id']}_"
    for start in (0, 5, 10):
        for index in range(start, min(start + 5, 12)):
            at.radio(key=prefix + str(index)).set_value(quiz['questions'][index]['correct_answer']).run()
        if start < 10:
            at.button(key='adaptive_next').click().run()
    assert at.get('progress')[0].proto.text == 'Answered 12 / 12'
    assert at.button(key='adaptive_unanswered').disabled
    at.button(key='submit_adaptive').click().run()
    assert not at.exception
    assert at.session_state['workspace']['active_quiz']['submitted']
    assert len(at.session_state['workspace']['question_history']) == 12
    assert len(at.session_state['workspace']['quiz_attempts']) == 1
    at.run()
    assert len(at.session_state['workspace']['question_history']) == 12
    assert next(m for m in at.metric if m.label == 'Practice score').value == '12 / 12'


def test_adaptive_count_follows_available_pool_and_empty_missed_selection():
    at = app().switch_page('pages/examination.py').run()
    at.segmented_control(key='practice_mode').set_value('Mixed and adaptive').run()
    at.multiselect(key='practice_groups').set_value(['Artifacts']).run()
    assert not at.exception
    assert at.number_input(key='practice_count').value == 1
    assert at.number_input(key='practice_count').max == 1
    at.checkbox(key='practice_missed').set_value(True).run()
    assert not at.exception
    assert at.button(key='start_adaptive').disabled
    assert at.number_input(key='practice_count').disabled
    assert any('No questions match this selection' in item.value for item in at.info)


def test_species_quiz_feedback_identifies_unanswered_questions_without_scoring():
    at = app().switch_page('pages/examination.py').run()
    at.selectbox(key='exam_species').set_value('ascaris_lumbricoides').run()
    questions = quiz_questions('ascaris_lumbricoides')
    at.radio[0].set_value(questions[0]['correct_answer'])
    next(b for b in at.button if b.label == 'Submit answers').click().run()
    assert not at.exception
    assert any('Answered 1 / 3' in item.value and '2, 3' in item.value for item in at.warning)
    assert not at.session_state['workspace']['question_history']
