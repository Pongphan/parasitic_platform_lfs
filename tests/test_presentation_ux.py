"""Task entry points and searchable collection coverage stay usable across reruns."""
from pathlib import Path

import pytest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.testing.v1 import AppTest

from content import atlas_entries


APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(autouse=True)
def explicit_navigation(monkeypatch):
    # Match the live st.navigation runtime rather than AppTest legacy discovery.
    original = PagesManager.__init__

    def initialize(manager, *args, **kwargs):
        PagesManager.uses_pages_directory = False
        original(manager, *args, **kwargs)

    monkeypatch.setattr(PagesManager, "__init__", initialize)


@pytest.mark.parametrize("action,target_widget", [
    ("home_atlas_action", "atlas_species"),
    ("home_detector_action", "detector_source"),
    ("home_practice_action", "exam_species"),
])
def test_home_task_buttons_reach_their_workflows(action, target_widget):
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.button(key=action).click().run()
    assert not at.exception
    widgets = [*at.selectbox, *at.segmented_control]
    assert any(widget.key == target_widget for widget in widgets)
    assert len([button for button in at.button if button.key and button.key.startswith("nav_")]) == 5


def test_home_coverage_search_handles_names_groups_and_no_matches():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.text_input(key="home_practice_search").set_value("  gIaRdIa  ").run()
    assert not at.exception
    assert at.dataframe[0].value["Atlas entry"].tolist() == [
        entry["name"] for entry in atlas_entries() if "giardia" in entry["name"].casefold()
    ]
    at.text_input(key="home_practice_search").set_value("blood parasites").run()
    assert not at.exception
    assert set(at.dataframe[0].value["Atlas entry"]) == {
        entry["name"] for entry in atlas_entries() if entry["group"] == "Blood parasites"
    }
    at.text_input(key="home_practice_search").set_value("[no matching entry]").run()
    assert not at.exception and not at.dataframe
    assert any("No Atlas entries match" in item.value for item in at.info)
    at.text_input(key="home_practice_search").set_value("").run()
    assert len(at.dataframe[0].value) == len(atlas_entries())
