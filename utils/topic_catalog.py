import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flask import abort
from werkzeug.utils import secure_filename


COURSE_CATALOG_PATH = Path("data/course_catalog.json")


def _load_course_catalog():
    with COURSE_CATALOG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_course_catalog(course_catalog):
    with COURSE_CATALOG_PATH.open("w", encoding="utf-8") as file:
        json.dump(course_catalog, file, indent=2)


def _build_topic_index(course_catalog):
    topics = {}
    for unit in course_catalog["units"]:
        for topic in unit["topics"]:
            item = topic.copy()
            item["unit_title"] = unit["title"]
            topics[item["slug"]] = item
    return topics


def _slugify(value):
    return secure_filename((value or "").strip().lower()).replace("-", "_")


def extract_youtube_video_id(url):
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("Enter a valid YouTube video link.")

    # Allow directly entering a raw 11-char YouTube video id.
    if len(cleaned) == 11 and all(ch.isalnum() or ch in "_-" for ch in cleaned):
        return cleaned

    parsed = urlparse(cleaned)
    host = (parsed.netloc or "").lower()
    path_parts = [part for part in (parsed.path or "").split("/") if part]

    candidates = []

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        candidates.append(path_parts[0])

    if "youtube.com" in host or "youtube-nocookie.com" in host:
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if query_id:
            candidates.append(query_id)

        if path_parts and path_parts[0] in {"embed", "shorts", "live", "v"} and len(path_parts) > 1:
            candidates.append(path_parts[1])

    for candidate in candidates:
        if len(candidate) == 11 and all(ch.isalnum() or ch in "_-" for ch in candidate):
            return candidate

    raise ValueError("Enter a valid YouTube video link.")


def get_course():
    return _load_course_catalog()


def list_units():
    return get_course()["units"]


def list_topics():
    return list(_build_topic_index(get_course()).values())


def get_default_topic():
    course = get_course()
    for unit in course["units"]:
        if unit.get("topics"):
            return unit["topics"][0]["slug"]
    return None


def get_topic(topic_slug):
    topic = _build_topic_index(get_course()).get(topic_slug)
    if not topic:
        return None
    return topic.copy()


def get_topic_or_404(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        abort(404)
    return topic


def create_unit(title):
    course = get_course()
    cleaned_title = (title or "").strip()
    if not cleaned_title:
        raise ValueError("Unit title is required.")

    slug = _slugify(cleaned_title)
    if any(unit["slug"] == slug for unit in course["units"]):
        raise ValueError("A unit with that title already exists.")

    new_unit = {
        "slug": slug,
        "title": cleaned_title,
        "topics": [],
    }
    course["units"].append(new_unit)
    _save_course_catalog(course)
    return new_unit


def create_topic(unit_slug, title, description, youtube_url, no_video=False):
    course = get_course()
    cleaned_title = (title or "").strip()
    cleaned_description = (description or "").strip()

    if not unit_slug:
        raise ValueError("Select a unit.")
    if not cleaned_title:
        raise ValueError("Topic title is required.")

    slug = _slugify(cleaned_title)
    if slug in {topic["slug"] for topic in _build_topic_index(course).values()}:
        raise ValueError("A topic with that title already exists.")

    video_id = ""
    if not no_video:
        video_id = extract_youtube_video_id(youtube_url)

    for unit in course["units"]:
        if unit["slug"] == unit_slug:
            new_topic = {
                "slug": slug,
                "title": cleaned_title,
                "unit_slug": unit_slug,
                "subject": course["title"],
                "description": cleaned_description or "New topic added by teacher.",
                "video_id": video_id,
                "has_video": not no_video,
            }
            unit["topics"].append(new_topic)
            _save_course_catalog(course)
            return new_topic

    raise ValueError("Selected unit does not exist.")
