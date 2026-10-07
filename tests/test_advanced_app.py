from test_app import app
from test_workspace import png, record, detection
from workspace import new_workspace, retain_image, add_record
from component_ai.jobs import prepare_job


def advanced(at):
    at.switch_page('pages/detector.py').run()
    at.radio(key='detector_workspace').set_value('Advanced workspace').run()
    assert not at.exception
    return at


def test_advanced_navigation_empty_states_and_bookmarks():
    at = advanced(app())
    for tool in ['Ground-truth evaluation','Session workspace','Batch and comparison']:
        at.radio(key='workspace_tool').set_value(tool).run()
        assert not at.exception
    at.switch_page('pages/atlas.py').run()
    species = at.selectbox(key='atlas_species').value
    at.button(key='atlas_bookmark').click().run()
    assert species in at.session_state['workspace']['bookmarks']
    assert not at.exception
    at.switch_page('pages/home.py').run()
    at.switch_page('pages/atlas.py').run()
    assert species in at.session_state['workspace']['bookmarks']


def test_adaptive_partial_answers_navigation_submission_and_importable_history():
    at = app().switch_page('pages/examination.py').run()
    at.segmented_control(key='practice_mode').set_value('Mixed and adaptive').run()
    at.number_input(key='practice_count').set_value(2).run()
    at.button(key='start_adaptive').click().run()
    assert not at.exception
    quiz = at.session_state['workspace']['active_quiz']
    first = f"adaptive_{quiz['id']}_0"
    at.radio(key=first).set_value(quiz['questions'][0]['correct_answer']).run()
    at.switch_page('pages/atlas.py').run()
    at.switch_page('pages/examination.py').run()
    assert at.radio(key=first).value == quiz['questions'][0]['correct_answer']
    at.button(key='submit_adaptive').click().run()
    assert at.warning
    second = f"adaptive_{quiz['id']}_1"
    at.radio(key=second).set_value(quiz['questions'][1]['correct_answer']).run()
    at.button(key='submit_adaptive').click().run()
    assert not at.exception
    assert len(at.session_state['workspace']['question_history']) == 2
    assert at.session_state['workspace']['active_quiz']['submitted']
    from session_archive import export_session, import_session
    assert import_session(export_session(at.session_state['workspace']))['active_quiz']['submitted']


def test_review_ui_saves_separate_layer_and_undo():
    at = app()
    ws = new_workspace(); retain_image(ws,png()); r = add_record(ws,record())
    at.session_state['workspace'] = ws
    advanced(at)
    at.radio(key='workspace_tool').set_value('Session workspace').run()
    assert not at.exception
    next(widget for widget in at.selectbox if widget.label == 'Object to review').set_value('0').run()
    next(widget for widget in at.selectbox if widget.label == 'Review status').set_value('corrected')
    next(widget for widget in at.text_input if widget.label == 'Reviewer class label').set_value('artifact')
    next(button for button in at.button if button.label == 'Save annotation').click().run()
    assert not at.exception
    saved = at.session_state['workspace']['records'][0]
    assert saved['review']['0']['class_name'] == 'artifact'
    assert saved['original']['detections'][0]['class_name'] == 'egg'
    next(button for button in at.button if button.label == 'Undo last annotation change').click().run()
    assert not at.exception
    assert not at.session_state['workspace']['records'][0]['review']


def test_batch_ui_fake_model_once_per_queue_item(monkeypatch):
    import component_layout.workbench as workbench
    from component_ai.jobs import step_job
    calls = []
    def runner(image, config):
        calls.append(config)
        return {'detections':[detection()]}
    monkeypatch.setattr(workbench,'step_job',lambda ws,job:step_job(ws,job,runner))
    at = app()
    ws = new_workspace()
    job = prepare_job(ws,[('image.png',png())],[{'mode':'auto','selected_model':'fake'}])
    at.session_state['workspace'] = ws
    at.session_state['analysis_job'] = job
    advanced(at)
    next(button for button in at.button if button.label == 'Start / resume queue').click().run()
    assert not at.exception
    assert len(calls) == 1
    at.run()
    assert not at.exception and len(calls) == 1
    assert at.session_state['analysis_job']['items'][0]['status'] == 'completed'


def test_comparison_ui_reports_and_saves_agreement():
    at = app(); ws = new_workspace(); retain_image(ws,png())
    r1 = add_record(ws,record()); r2 = add_record(ws,record())
    r2['configuration']['selected_model'] = 'other'
    at.session_state['workspace'] = ws
    advanced(at)
    at.multiselect(key='comparison_ids').set_value([r1['analysis_id'],r2['analysis_id']]).run()
    assert not at.exception
    at.button(key='comparison_save').click().run()
    assert len(at.session_state['workspace']['comparisons']) == 1


def test_evaluation_ui_known_fixture(monkeypatch):
    import io
    import streamlit as st
    from workspace import json_bytes
    from test_workspace import coco
    original = st.file_uploader
    def uploader(label,*args,**kwargs):
        return io.BytesIO(json_bytes(coco())) if label == 'COCO bounding-box JSON' else original(label,*args,**kwargs)
    monkeypatch.setattr(st,'file_uploader',uploader)
    at = app(); ws = new_workspace(); retain_image(ws,png()); r = add_record(ws,record())
    at.session_state['workspace'] = ws
    advanced(at)
    at.radio(key='workspace_tool').set_value('Ground-truth evaluation').run()
    next(w for w in at.multiselect if w.label == 'Analyses to evaluate').set_value([r['analysis_id']]).run()
    at.text_input(key='eval_map_1').set_value('egg').run()
    next(b for b in at.button if b.label == 'Evaluate selected analyses').click().run()
    assert not at.exception
    assert at.session_state['evaluation_report']['overall']['tp'] == 1
    assert at.session_state['evaluation_report']['overall']['f1'] == 1


def test_session_import_ui_replaces_only_after_validated_action(monkeypatch):
    import io
    import streamlit as st
    from session_archive import export_session
    ws = new_workspace(); add_record(ws,record())
    data = export_session(ws)
    original = st.file_uploader
    def uploader(label,*args,**kwargs):
        return io.BytesIO(data) if kwargs.get('key') == 'session_import' else original(label,*args,**kwargs)
    monkeypatch.setattr(st,'file_uploader',uploader)
    at = advanced(app())
    at.radio(key='workspace_tool').set_value('Session workspace').run()
    restore = at.button(key='session_restore')
    assert restore.disabled
    at.checkbox(key='session_replace').set_value(True).run()
    at.button(key='session_restore').click().run()
    assert not at.exception
    assert at.session_state['workspace']['records'][0]['analysis_id'] == ws['records'][0]['analysis_id']
    assert not at.session_state['workspace']['images']
