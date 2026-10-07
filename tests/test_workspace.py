import io
import json
import zipfile
from copy import deepcopy
import pytest
from PIL import Image
from workspace import (new_workspace, retain_image, analysis_record, add_record, update_review,
                       undo_review, final_annotations, digest, enforce_limits, json_bytes)
from session_archive import export_session, import_session, dataset_export, batch_export, zip_files
from component_ai.jobs import prepare_job, step_job, cancel_job, retry_failed
from component_ai.comparison import match_boxes, evaluate, validate_coco
from content import atlas_entries
from learning import question_pool, select_questions, start_quiz, submit_active


def png(color='white', size=(40,30)):
    data = io.BytesIO()
    Image.new('RGB', size, color).save(data, format='PNG')
    return data.getvalue()


def detection(label='egg', box=None, confidence=0.9):
    return {'class_name': label, 'class_id': 1, 'confidence': confidence, 'bbox_xyxy': box or [2,3,12,13]}


def record(data=None, name='sample.png'):
    data = data or png()
    return analysis_record({'image_sha256':digest(data), 'image_name':name,
                            'configuration':{'mode':'auto', 'selected_model':'fake', 'confidence':0.5},
                            'model_sha256':{'fake':'a'*64}, 'detections':[detection()]}, 40,30)


def coco():
    return {'images':[{'id':1,'file_name':'sample.png','width':40,'height':30}],
            'categories':[{'id':1,'name':'egg'}],
            'annotations':[{'id':1,'image_id':1,'category_id':1,'bbox':[2,3,10,10]}]}


def test_original_immutable_review_undo_and_explicit_exports():
    r = record()
    original = deepcopy(r['original'])
    with pytest.raises(ValueError, match='corrected'):
        update_review(r,'0','accepted','artifact',[2,3,12,13])
    update_review(r,'0','corrected','artifact',[1,1,15,15],'shell detail')
    added = update_review(r,None,'corrected','egg',[20,10,30,25])
    assert r['original'] == original
    assert len(final_annotations(r)) == 2
    with pytest.raises(ValueError, match='mapping'):
        dataset_export([r], ['egg'])
    archive, result = dataset_export([r], ['artifact','egg'])
    assert result['annotations'][0]['bbox'] == [1,1,14,14]
    assert result['info']['origin'].startswith('human_review')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        parts = z.read(f"labels/{r['analysis_id']}.txt").decode().splitlines()[0].split()
        assert int(parts[0]) == 0
        assert float(parts[1]) == pytest.approx(8/40)
    undo_review(r)
    assert added not in r['review']
    undo_review(r)
    assert r['review'] == {} and r['original'] == original
    assert not final_annotations(r)


@pytest.mark.parametrize('box', [[-1,0,2,2],[0,0,0,5],[0,0,41,20],[0,0,float('nan'),20]])
def test_invalid_boxes_do_not_mutate_record(box):
    r = record()
    with pytest.raises(ValueError):
        update_review(r,'0','corrected','egg',box)
    assert r['review'] == {} and r['review_undo'] == []


def test_batch_failure_isolation_retry_cancel_and_deduplication():
    ws = new_workspace()
    config = {'mode':'auto','selected_model':'fake'}
    job = prepare_job(ws,[('one.png',png()),('duplicate.png',png()),('two.png',png('blue')),('bad.png',b'bad')],[config])
    assert len(job['items']) == 3 and job['items'][-1]['status'] == 'validation_failed'
    calls = []
    def runner(image, config):
        calls.append(image.getpixel((0,0)))
        if len(calls) == 2:
            raise RuntimeError('independent failure')
        return {'detections':[detection()]}
    job['running'] = True
    step_job(ws,job,runner)
    cancel_job(job)
    assert step_job(ws,job,runner) is None and len(calls) == 1
    job.update(running=True,cancelled=False)
    step_job(ws,job,runner)
    assert job['items'][0]['status'] == 'completed' and job['items'][1]['status'] == 'failed'
    retry_failed(job)
    step_job(ws,job,runner)
    assert len(calls) == 3 and job['items'][1]['status'] == 'completed'
    step_job(ws,job,runner)
    assert len(calls) == 3
    from component_ai.jobs import job_records
    data = batch_export(ws,job_records(ws,job),job)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert 'summary.csv' in z.namelist()
        assert sum(name.endswith('.png') for name in z.namelist()) == 2


def test_retention_eviction_preserves_reports_and_requires_matching_bytes():
    ws = new_workspace()
    ws['image_budget'] = len(png()) + 40*30*3 + 20
    first, _ = retain_image(ws,png())
    r = add_record(ws,record())
    retain_image(ws,png('blue'))
    assert first not in ws['images'] and r in ws['records']
    with pytest.raises(ValueError, match='SHA-256'):
        retain_image(ws,png('red'),first)
    ws['record_limit'] = 1
    add_record(ws,record(png('blue')))
    assert len(ws['records']) == 1


def test_matching_is_one_to_one_and_class_aware():
    match = match_boxes([detection(),detection(confidence=.8),detection('artifact')],[detection()],.5)
    assert len(match['matches']) == 1
    assert match['matches'][0]['prediction'] == 0
    assert set(match['unmatched_predictions']) == {1,2}


def test_evaluation_known_counts_and_missing_vs_empty_images():
    first = record()
    first['original']['detections'].append(detection(box=[20,10,30,20]))
    unknown = record(png('blue'),'unknown.png')
    empty = record(png('red'),'empty.png')
    data = coco()
    data['images'].append({'id':2,'file_name':'empty.png','width':40,'height':30})
    result = evaluate([first,unknown,empty],data,{'egg':'egg'},.7,.5)
    assert result['overall']['tp'] == 1
    assert result['overall']['fp'] == 2
    assert result['overall']['fn'] == 0
    assert result['overall']['precision'] == pytest.approx(1/3)
    assert result['overall']['f1'] == .5
    assert len(result['excluded']) == 1 and result['excluded'][0]['analysis_id'] == unknown['analysis_id']


@pytest.mark.parametrize('mutation', [
    lambda d:d['annotations'].append(deepcopy(d['annotations'][0])),
    lambda d:d['annotations'][0].update(iscrowd=1),
    lambda d:d['annotations'][0].update(category_id=999),
    lambda d:d['annotations'][0].update(bbox=[0,0,-2,3]),
    lambda d:d['images'][0].update(width=0),
])
def test_invalid_coco_rejected(mutation):
    data = coco(); mutation(data)
    with pytest.raises(ValueError):
        validate_coco(data)


def test_session_roundtrip_with_and_without_images_and_learning():
    ws = new_workspace()
    retain_image(ws,png())
    r = add_record(ws,record())
    update_review(r,'0','accepted','egg',[2,3,12,13])
    pool = question_pool(atlas_entries())
    quiz = start_quiz(ws,pool[:2])
    submit_active(ws,[q['correct_answer'] for q in quiz['questions']],[None,'High'])
    ws['bookmarks'] = [pool[0]['species_id']]
    ws['learning_lists'] = {'Example':ws['bookmarks'][:]}
    for include in (False,True):
        restored = import_session(export_session(ws,include))
        assert restored['records'][0]['original'] == r['original']
        assert restored['records'][0]['review'] == r['review']
        assert bool(restored['images']) == include
        assert restored['question_history'] == ws['question_history']
        assert restored['active_quiz'] == quiz


@pytest.mark.parametrize('path', ['../outside.txt','C:/unsafe.txt','images/../../bad','payload.pkl'])
def test_archive_rejects_unsafe_or_executable_members(path):
    with pytest.raises(ValueError):
        import_session(zip_files({'session.json':b'{}',path:b'bad'}))


def test_archive_rejects_duplicates_unsupported_schema_and_malformed_records():
    ws = new_workspace(); add_record(ws,record())
    original = export_session(ws)
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        data = json.loads(z.read('session.json'))
    for mutation in (lambda d:d.update(schema_version='future'),
                     lambda d:d['records'][0]['image'].update(width=-1),
                     lambda d:d['records'][0]['original']['detections'][0].update(confidence=3),
                     lambda d:d.update(bookmarks=['invented_species'])):
        changed = deepcopy(data); mutation(changed)
        with pytest.raises(ValueError):
            import_session(zip_files({'session.json':json_bytes(changed)}))
    with pytest.raises(ValueError):
        import_session(zip_files({'session.json':b'{"schema_version":"2027.2","schema_version":"2027.2"}'}))
    with pytest.raises(ValueError, match='compression'):
        import_session(zip_files({'session.json':b' '*2_000_000}))


def test_adaptive_recent_errors_unique_questions_and_submit_idempotency():
    ws = new_workspace(); pool = question_pool(atlas_entries())
    quiz = start_quiz(ws,pool[:3])
    answers = [(q['correct_answer']+1)%len(q['options']) for q in quiz['questions']]
    submit_active(ws,answers,[None]*3)
    submit_active(ws,answers,[None]*3)
    assert len(ws['question_history']) == 3
    selected = select_questions(pool+pool,ws['question_history'],20,missed_only=True)
    assert len(selected) == 3
    assert selected[0]['question_key'] == pool[2]['question_key']
    assert len({q['question_key'] for q in selected}) == 3


def test_optional_ml_runtimes_are_not_imported_by_learning_and_workspace():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-c',
        "import sys; import component_layout.workbench, component_layout.learning; "
        "assert not any(n in sys.modules for n in ('tensorflow','torch','torchvision','ultralytics'))"],
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_archive_wrong_image_hash_and_dimension_mismatch():
    ws = new_workspace(); retain_image(ws,png()); add_record(ws,record())
    archive = export_session(ws,True)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        files = {name:z.read(name) for name in z.namelist()}
    member = next(name for name in files if name.startswith('images/'))
    bad = {**files, member:png('blue')}
    with pytest.raises(ValueError,match='SHA-256'):
        import_session(zip_files(bad))
    metadata = json.loads(files['session.json'])
    metadata['records'][0]['image']['width'] = 41
    files['session.json'] = json_bytes(metadata)
    with pytest.raises(ValueError,match='dimensions'):
        import_session(zip_files(files))


def test_budget_rejection_failed_history_and_evicted_retry():
    ws = new_workspace(); ws['image_budget'] = 5000
    job = prepare_job(ws,[('a.png',png()),('b.png',png('blue'))],[{'mode':'auto','selected_model':'fake'}])
    assert job['items'][1]['status'] == 'validation_failed'
    ws['images'].clear(); job['running'] = True
    step_job(ws,job,lambda *args:pytest.fail('Should not run without image'))
    assert job['items'][0]['status'] == 'failed'
    retain_image(ws,png()); retry_failed(job)
    step_job(ws,job,lambda *args:{'detections':[]})
    assert job['items'][0]['status'] == 'completed'


def test_evaluation_rejects_incompatible_runs_and_preserves_origin():
    first = record(); second = record(png('blue'),'other.png')
    second['configuration']['confidence'] = .8
    with pytest.raises(ValueError,match='configuration'):
        evaluate([first,second],coco(),{'egg':'egg'})
    with pytest.raises(ValueError,match='one analysis'):
        evaluate([first,record()],coco(),{'egg':'egg'})
    references = coco(); references['images'][0]['sha256'] = first['image']['sha256']
    references['images'][0]['file_name'] = 'renamed.png'
    references['info'] = {'origin':'human_review_of_model_predictions'}
    result = evaluate([first],references,{'egg':'egg'})
    assert result['images'][0]['identity_method'] == 'sha256'
    assert result['reference_origin'] == 'human_review_of_model_predictions'
