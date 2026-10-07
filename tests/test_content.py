import json
import pytest
from content import atlas_entries, quiz_questions, grade, local_asset, filter_atlas, atlas_for_model_label, localized_entry, export_atlas

def test_bundled_species_and_quizzes_are_consistent():
    entries = atlas_entries()
    assert len(entries) >= 50
    assert {"necator_americanus", "ancylostoma_ceylanicum", "taenia_spp", "fasciolopsis_buski", "strongyloides_stercoralis"}.issubset({e["id"] for e in entries})
    for entry in entries:
        assert entry["classification_label"]
        assert entry["images"], f"Missing local schematic for {entry['id']}"
        if entry["id"] not in ("opisthorchis_viverrini", "minute_intestinal_flukes", "artifacts"):
            assert entry["classifier_labels"] == []
        for image in entry["images"]:
            assert local_asset(entry["folder"], image["file"]).exists()
        questions = quiz_questions(entry["id"])
        assert questions
        assert all(grade(questions, [q["correct_answer"] for q in questions]))
        assert not any(grade(questions, [(q["correct_answer"]+1) % len(q["options"]) for q in questions]))
        with pytest.raises(ValueError, match="every question"):
            grade(questions, [None] * len(questions))

def test_bad_quiz_and_asset_traversal(tmp_path):
    with pytest.raises(ValueError):
        local_asset(tmp_path, "../secret.txt")
    with pytest.raises(ValueError):
        quiz_questions("../escape")
    folder = tmp_path / "test_species"
    folder.mkdir()
    (folder / "quiz.json").write_text(json.dumps({"species_id":"test_species", "questions":[{"id":"q1", "question":"Q?", "options":["a","b"], "correct_answer":2, "explanation":"why"}]}))
    with pytest.raises(ValueError, match="answer index"):
        quiz_questions("test_species", tmp_path)


def test_expanded_records_and_portable_export():
    entries = atlas_entries()
    assert {"Nematodes", "Cestodes", "Trematodes", "Protozoa", "Blood parasites", "Artifacts"} == {e["group"] for e in entries}
    for entry in entries:
        assert entry["schema_version"] == 2
        for key in ("taxonomy", "specimen", "diagnostics", "hosts", "distribution", "differential_diagnosis", "annotation_guidance", "reference_images"):
            assert entry[key]
        assert entry["language"] == "en" and isinstance(entry["translations"], dict)
        assert all(s["url"].startswith("https://") for s in entry["references"] + entry["reference_images"])
    restored = json.loads(export_atlas(entries))
    assert len(restored) == len(entries)
    assert all("folder" not in item for item in restored)


def test_model_mapping_preserves_uncertainty():
    assert atlas_for_model_label("class_1")["id"] == "opisthorchis_viverrini"
    assert atlas_for_model_label("class_2")["id"] == "minute_intestinal_flukes"
    assert atlas_for_model_label("artifact")["id"] == "artifacts"
    for unknown in ("class_0", "Haplorchis taichui", "Hd", "Hn", "Hw", "unknown", "egg"):
        assert atlas_for_model_label(unknown) is None


def test_combined_filters_synonyms_and_translation_fallback():
    entries = atlas_entries()
    assert [e["id"] for e in filter_atlas(entries, "Giardia lamblia")] == ["giardia_duodenalis"]
    assert [e["id"] for e in filter_atlas(entries, "class_2")] == ["minute_intestinal_flukes"]
    assert filter_atlas(entries, "", "Blood parasites", "Vector-borne", "Anemia")
    assert not filter_atlas(entries, "", "Cestodes", "Vector-borne")
    entry = next(e for e in entries if e["id"] == "giardia_duodenalis")
    assert localized_entry(entry, "th") == entry
    entry["translations"]["th"] = {"common_name": "ไกอาร์เดีย", "id": "must_not_change"}
    translated = localized_entry(entry, "th")
    assert translated["common_name"] == "ไกอาร์เดีย"
    assert translated["id"] == entry["id"]
    assert entry["common_name"] != translated["common_name"]
