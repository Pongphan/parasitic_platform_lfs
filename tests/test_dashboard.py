from component_layout.dashboard import record_activity

def test_session_activity_is_bounded_and_does_not_count_crops_as_objects():
    state = {}
    base = {"created_at":"2026-09-07T10:00:00+00:00", "configuration":{"mode":"keras"}, "predictions":[{}], "errors":[]}
    for _ in range(205):
        record_activity(state, base)
    assert len(state["analysis_activity"]) == 200
    assert all(row["Objects"] == 0 for row in state["analysis_activity"])
    record_activity(state, {**base,"predictions":[],"errors":["bad output"]})
    assert state["analysis_activity"][-1]["Status"] == "Failed"
    record_activity(state, {**base,"configuration":{"mode":"yolo"}, "detections":[{},{}]})
    assert state["analysis_activity"][-1]["Objects"] == 2
    assert set(state["analysis_activity"][-1]) == {"Time","Family","Status","Objects"}
