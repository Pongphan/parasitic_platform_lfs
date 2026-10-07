"""Explainable, session-only learning selection and attempt history."""
from collections import Counter
from copy import deepcopy
import uuid
from content import quiz_questions, grade
from workspace import now, enforce_limits


def question_pool(entries, groups=None):
    return [{**q, "species_id": entry["id"], "species_name": entry["name"], "group": entry["group"],
             "question_key": entry["id"] + ":" + q["id"]}
            for entry in entries if not groups or entry["group"] in groups for q in quiz_questions(entry["id"])]


def select_questions(pool, history, count, missed_only=False):
    counts = Counter(row["question_key"] for row in history)
    latest = {row["question_key"]: (i, row["correct"]) for i, row in enumerate(history)}
    unique = {q["question_key"]: q for q in pool}
    candidates = [q for key, q in unique.items() if not missed_only or (key in latest and not latest[key][1])]
    def priority(q):
        key = q["question_key"]
        index, correct = latest.get(key, (-1, True))
        return (0 if not correct else 1, -index if not correct else counts[key], key)
    return deepcopy(sorted(candidates, key=priority)[:count])


def start_quiz(ws, questions):
    if not questions:
        raise ValueError("No questions match this practice selection.")
    ws["active_quiz"] = {"id": uuid.uuid4().hex, "questions": deepcopy(questions), "answers": [None]*len(questions),
                         "confidence": [None]*len(questions), "submitted": False, "created_at": now()}
    return ws["active_quiz"]


def submit_active(ws, answers, confidence):
    quiz = ws["active_quiz"]
    if quiz["submitted"]:
        return quiz
    correct = grade(quiz["questions"], answers)
    if len(confidence) != len(answers) or any(v not in (None, "Low", "Medium", "High") for v in confidence):
        raise ValueError("Invalid confidence rating.")
    quiz.update(answers=list(answers), confidence=list(confidence), correct=correct, submitted=True)
    for q, answer, rating, success in zip(quiz["questions"], answers, confidence, correct):
        ws["question_history"].append({"question_key": q["question_key"], "species_id": q["species_id"],
                                      "group": q["group"], "answer": answer, "confidence": rating,
                                      "correct": success, "created_at": now(), "quiz_id": quiz["id"]})
    ws["quiz_attempts"][quiz["id"]] = deepcopy(quiz)
    while len(ws["quiz_attempts"]) > 100:
        del ws["quiz_attempts"][next(iter(ws["quiz_attempts"]))]
    enforce_limits(ws)
    return quiz


def related_entries(entry, entries):
    """Only declared taxonomic groups, clinical tags and related Atlas IDs."""
    related_id = entry.get("model_mapping", {}).get("related_atlas_id")
    rows = []
    for candidate in entries:
        if candidate["id"] == entry["id"]:
            continue
        reasons = []
        if candidate["id"] == related_id:
            reasons.append("Declared related morphology group")
        if candidate["group"] == entry["group"]:
            reasons.append("Same taxonomic category")
        tags = sorted(set(entry.get("clinical_tags", [])) & set(candidate.get("clinical_tags", [])))
        if tags:
            reasons.append("Shared content tags: " + ", ".join(tags))
        if reasons:
            rows.append((candidate, reasons))
    return sorted(rows, key=lambda row: (row[0]["id"] != related_id, -len(row[1]), row[0]["name"]))[:5]
