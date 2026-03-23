import json
from datetime import datetime, timezone
from pathlib import Path

from utils.topic_catalog import list_units


TOPIC_MCQ_PATH = Path("data/topic_mcq_bank.json")
TOPIC_PROGRESS_PATH = Path("data/student_topic_progress.json")
PASS_PERCENTAGE = 80.0
_JSON_CACHE = {}


def _load_json(path, default):
    if not path.exists():
        _JSON_CACHE[str(path)] = {
            "mtime": None,
            "payload": default,
        }
        return default

    mtime = path.stat().st_mtime
    cache_entry = _JSON_CACHE.get(str(path))
    if cache_entry and cache_entry.get("mtime") == mtime:
        return cache_entry.get("payload", default)

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(default, dict) and not isinstance(payload, dict):
        payload = default
    if isinstance(default, list) and not isinstance(payload, list):
        payload = default

    _JSON_CACHE[str(path)] = {
        "mtime": mtime,
        "payload": payload,
    }
    return payload


def _save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    _JSON_CACHE[str(path)] = {
        "mtime": path.stat().st_mtime,
        "payload": payload,
    }


def _normalize_question(item):
    if not isinstance(item, dict):
        raise ValueError("Each question must be an object.")

    question = str(item.get("question") or "").strip()
    if not question:
        raise ValueError("Each question must include 'question'.")

    options = item.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError("Each question must include at least 2 options.")

    cleaned_options = [str(option or "").strip() for option in options]
    if any(not option for option in cleaned_options):
        raise ValueError("Options cannot be empty.")

    answer_index = item.get("answer_index")
    if not isinstance(answer_index, int):
        raise ValueError("Each question must include integer 'answer_index'.")

    if answer_index < 0 or answer_index >= len(cleaned_options):
        raise ValueError("answer_index is out of range for options.")

    return {
        "question": question,
        "options": cleaned_options,
        "answer_index": answer_index,
    }


def save_topic_mcqs(topic_slug, raw_questions):
    cleaned_topic = str(topic_slug or "").strip()
    if not cleaned_topic:
        raise ValueError("Topic is required.")

    if isinstance(raw_questions, dict):
        questions = raw_questions.get("questions")
    else:
        questions = raw_questions

    if not isinstance(questions, list) or not questions:
        raise ValueError("JSON must include a non-empty questions list.")

    normalized = [_normalize_question(item) for item in questions]

    payload = _load_json(TOPIC_MCQ_PATH, {})
    payload[cleaned_topic] = normalized
    _save_json(TOPIC_MCQ_PATH, payload)
    return normalized


def get_topic_mcqs(topic_slug):
    cleaned_topic = str(topic_slug or "").strip()
    if not cleaned_topic:
        return []

    payload = _load_json(TOPIC_MCQ_PATH, {})
    questions = payload.get(cleaned_topic, [])
    if not isinstance(questions, list):
        return []
    return questions


def get_topic_mcqs_for_student(topic_slug):
    questions = get_topic_mcqs(topic_slug)
    redacted = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        redacted.append(
            {
                "question": item.get("question", ""),
                "options": item.get("options", []),
            }
        )
    return redacted


def _topic_order():
    ordered = []
    for unit in list_units():
        for topic in unit.get("topics", []):
            slug = str(topic.get("slug") or "").strip()
            if slug:
                ordered.append(slug)
    return ordered


def get_topic_access_map(user_id):
    ordered = _topic_order()
    if not ordered:
        return {}

    progress = get_student_progress(user_id)
    access_map = {}
    for index, slug in enumerate(ordered):
        if index == 0:
            access_map[slug] = True
            continue

        previous_slug = ordered[index - 1]
        previous_state = progress.get(previous_slug, {})
        access_map[slug] = bool(previous_state.get("passed"))

    return access_map


def get_student_progress(user_id):
    payload = _load_json(TOPIC_PROGRESS_PATH, {})
    key = str(user_id)
    state = payload.get(key, {})
    if not isinstance(state, dict):
        return {}
    return state


def _save_student_progress(user_id, progress):
    payload = _load_json(TOPIC_PROGRESS_PATH, {})
    payload[str(user_id)] = progress
    _save_json(TOPIC_PROGRESS_PATH, payload)


def get_topic_result(user_id, topic_slug):
    state = get_student_progress(user_id)
    topic_state = state.get(str(topic_slug or "").strip(), {})
    if not isinstance(topic_state, dict):
        return {}
    return topic_state


def grade_mcq_attempt(topic_slug, answers):
    questions = get_topic_mcqs(topic_slug)
    total = len(questions)
    if total == 0:
        raise ValueError("MCQ is not uploaded yet for this topic.")

    if not isinstance(answers, list):
        raise ValueError("Answers must be a list.")

    correct = 0
    for index, item in enumerate(questions):
        expected = item.get("answer_index")
        selected = answers[index] if index < len(answers) else None
        if isinstance(selected, int) and selected == expected:
            correct += 1

    score = (correct / total) * 100.0 if total else 0.0
    passed = score > PASS_PERCENTAGE
    return {
        "total": total,
        "correct": correct,
        "score": round(score, 2),
        "passed": passed,
        "pass_percentage": PASS_PERCENTAGE,
    }


def save_attempt_result(user_id, topic_slug, result):
    state = get_student_progress(user_id)
    topic_key = str(topic_slug or "").strip()
    existing = state.get(topic_key, {}) if isinstance(state.get(topic_key), dict) else {}

    best_score = max(float(existing.get("best_score", 0.0)), float(result["score"]))
    best_passed = bool(existing.get("passed")) or bool(result["passed"])

    state[topic_key] = {
        "best_score": round(best_score, 2),
        "passed": best_passed,
        "last_score": float(result["score"]),
        "last_correct": int(result["correct"]),
        "last_total": int(result["total"]),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_student_progress(user_id, state)
    return state[topic_key]
