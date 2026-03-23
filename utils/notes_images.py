import json
from pathlib import Path


NOTES_IMAGES_PATH = Path("data/notes_images.json")
_NOTES_IMAGES_CACHE = {
    "mtime": None,
    "payload": None,
}


def _load_notes_images():
    if not NOTES_IMAGES_PATH.exists():
        _NOTES_IMAGES_CACHE["mtime"] = None
        _NOTES_IMAGES_CACHE["payload"] = {}
        return {}

    mtime = NOTES_IMAGES_PATH.stat().st_mtime
    if _NOTES_IMAGES_CACHE["payload"] is not None and _NOTES_IMAGES_CACHE["mtime"] == mtime:
        return _NOTES_IMAGES_CACHE["payload"]

    with NOTES_IMAGES_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        payload = {}

    _NOTES_IMAGES_CACHE["mtime"] = mtime
    _NOTES_IMAGES_CACHE["payload"] = payload
    return payload


def _save_notes_images(payload):
    NOTES_IMAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NOTES_IMAGES_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    _NOTES_IMAGES_CACHE["mtime"] = NOTES_IMAGES_PATH.stat().st_mtime
    _NOTES_IMAGES_CACHE["payload"] = payload


def get_notes_images(topic_slug):
    topic_key = str(topic_slug or "").strip()
    if not topic_key:
        return []

    payload = _load_notes_images()
    items = payload.get(topic_key, [])
    if not isinstance(items, list):
        return []

    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        cleaned.append({"title": title, "url": url})

    return cleaned


def add_notes_image(topic_slug, title, url):
    topic_key = str(topic_slug or "").strip()
    cleaned_title = str(title or "").strip()
    cleaned_url = str(url or "").strip()

    if not topic_key:
        raise ValueError("Topic is required.")
    if not cleaned_url:
        raise ValueError("Image URL is required.")

    payload = _load_notes_images()
    existing = payload.get(topic_key, [])
    if not isinstance(existing, list):
        existing = []

    entry = {"title": cleaned_title, "url": cleaned_url}
    existing.append(entry)
    payload[topic_key] = existing
    _save_notes_images(payload)
    return entry
