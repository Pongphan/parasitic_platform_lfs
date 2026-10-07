"""Strict, filesystem-based discovery of Atlas and assessment records."""
import json
from copy import deepcopy
from pathlib import Path
from component_ai.settings import canonical_label, canonical_labels

ROOT = Path(__file__).resolve().parent

def atlas_entries(root=ROOT / "pages" / "parasites"):
    entries = []
    for path in sorted(root.glob("*/content.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        required = ("id", "name", "common_name", "group", "description", "life_cycle", "morphology", "clinical_significance", "references", "reviewed_on")
        if any(not item.get(key) for key in required) or item["id"] != path.parent.name:
            raise ValueError(f"Invalid Atlas entry: {path.name} in {path.parent.name}")
        for field in ("life_cycle", "morphology", "images", "references"):
            if not isinstance(item[field], list):
                raise ValueError(f"{item['id']}: {field} must be a list")
        item["folder"] = path.parent
        item.setdefault("classification_label", item["id"].replace("_", " "))
        item.setdefault("classifier_labels", [])
        if not isinstance(item["classification_label"], str) or not item["classification_label"] or not isinstance(item["classifier_labels"], list) or any(not isinstance(label, str) or not label for label in item["classifier_labels"]):
            raise ValueError(f"Invalid classification metadata in {item['id']}")
        item["classification_label"] = canonical_label(item["classification_label"])
        item["classifier_labels"] = canonical_labels(item["classifier_labels"])
        if item.get("schema_version") == 2:
            for field in ("taxonomy", "transmission", "hosts", "distribution", "specimen", "diagnostics", "differential_diagnosis", "clinical_tags", "model_mapping", "annotation_guidance"):
                if not item.get(field):
                    raise ValueError(f"{item['id']}: missing {field}")
            if not item["images"] and not item.get("reference_images"):
                raise ValueError(f"{item['id']}: an illustration or reference gallery is required")
            if canonical_labels(item["model_mapping"]["exact_labels"]) != item["classifier_labels"]:
                raise ValueError(f"{item['id']}: inconsistent model labels")
        entries.append(item)
    ids = {e["id"] for e in entries}
    mapped = set()
    for entry in entries:
        related = entry.get("model_mapping", {}).get("related_atlas_id")
        if related and related not in ids:
            raise ValueError(f"{entry['id']}: unknown related Atlas entry")
        for label in entry["classifier_labels"]:
            if label.casefold() in mapped:
                raise ValueError(f"Ambiguous Atlas mapping: {label}")
            mapped.add(label.casefold())
    return entries


def filter_atlas(entries, query="", group="All groups", transmission="All routes", clinical="All clinical contexts"):
    """Reusable AND filters across names, synonyms and diagnostic reference fields."""
    words = query.casefold().split()
    matches = []
    for entry in entries:
        searchable = {k: entry.get(k) for k in ("name", "common_name", "aliases", "taxonomy", "morphology", "transmission", "distribution", "clinical_significance", "clinical_tags", "specimen", "classifier_labels", "model_mapping", "translations")}
        haystack = json.dumps(searchable, ensure_ascii=False).casefold()
        if (all(word in haystack for word in words)
                and (group == "All groups" or entry["group"] == group)
                and (transmission == "All routes" or transmission in entry["transmission"]["types"])
                and (clinical == "All clinical contexts" or clinical in entry["clinical_tags"])):
            matches.append(entry)
    return matches


def atlas_for_model_label(label, entries=None):
    """Resolve configured exact labels; never infer species from substrings or IDs."""
    normalized = canonical_label(label).casefold()
    return next((e for e in (atlas_entries() if entries is None else entries)
                 if normalized in [x.casefold() for x in e["classifier_labels"]]), None)


def localized_entry(entry, language="en"):
    """Translated display fields can override English; scientific/model IDs stay stable."""
    result = deepcopy(entry)
    allowed = {"common_name", "description", "morphology", "life_cycle", "clinical_significance", "hosts", "distribution", "specimen", "diagnostics", "differential_diagnosis", "annotation_guidance"}
    for key, value in entry.get("translations", {}).get(language, {}).items():
        if key in allowed and value:
            result[key] = deepcopy(value)
    return result


def export_atlas(entries):
    """Portable records without runtime filesystem paths."""
    return json.dumps([{k: v for k, v in e.items() if k != "folder"} for e in entries], ensure_ascii=False, indent=2)

def local_asset(folder, name):
    asset = (folder / name).resolve()
    if not asset.is_relative_to(folder.resolve()) or not asset.is_file():
        raise ValueError("Image must be an existing file inside its species folder")
    return asset

def quiz_questions(species_id, root=ROOT / "pages" / "parasites_quiz"):
    if not species_id.replace("_", "").isalnum():
        raise ValueError("Invalid species identifier")
    path = root / species_id / "quiz.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("species_id") != species_id or not isinstance(data.get("questions"), list):
        raise ValueError(f"Invalid quiz for {species_id}")
    ids = set()
    for q in data["questions"]:
        if not all(q.get(k) for k in ("id", "question", "options", "explanation")) or q["id"] in ids:
            raise ValueError(f"Missing fields or duplicate question in {species_id}")
        opts = q["options"]
        if not isinstance(opts, list) or len(opts) < 2 or len(set(opts)) != len(opts) or any(not isinstance(o, str) or not o for o in opts):
            raise ValueError(f"Invalid options in {species_id}")
        if type(q.get("correct_answer")) is not int or not 0 <= q["correct_answer"] < len(opts):
            raise ValueError(f"Invalid answer index in {species_id}")
        ids.add(q["id"])
    return data["questions"]

def grade(questions, answers):
    if len(answers) != len(questions) or any(a is None for a in answers):
        raise ValueError("Answer every question before submitting.")
    if any(type(a) is not int or not 0 <= a < len(q["options"]) for q, a in zip(questions, answers)):
        raise ValueError("Invalid answer selection")
    return [a == q["correct_answer"] for q, a in zip(questions, answers)]
