import json
from pathlib import Path
from urllib.parse import urlsplit


DATA_PATH = Path("data/topic_text_content.json")
_TEXT_CONTENT_CACHE = {
    "mtime": None,
    "payload": None,
}

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}


def _looks_like_image_url(url):
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False

    suffix = Path(parsed.path or "").suffix.lower()
    return bool(suffix and suffix in _IMAGE_EXTENSIONS)


def _load_all():
    if not DATA_PATH.exists():
        _TEXT_CONTENT_CACHE["mtime"] = None
        _TEXT_CONTENT_CACHE["payload"] = {}
        return {}

    mtime = DATA_PATH.stat().st_mtime
    if _TEXT_CONTENT_CACHE["payload"] is not None and _TEXT_CONTENT_CACHE["mtime"] == mtime:
        return _TEXT_CONTENT_CACHE["payload"]

    with DATA_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        data = {}

    _TEXT_CONTENT_CACHE["mtime"] = mtime
    _TEXT_CONTENT_CACHE["payload"] = data
    return data


def _save_all(content):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(content, file, indent=2)

    _TEXT_CONTENT_CACHE["mtime"] = DATA_PATH.stat().st_mtime
    _TEXT_CONTENT_CACHE["payload"] = content


def get_text_content(topic_slug):
    all_content = _load_all()
    entry = all_content.get(topic_slug) or {}

    extra_fields = entry.get("extra_fields") or []
    if not isinstance(extra_fields, list):
        extra_fields = []

    related_urls = entry.get("related_urls") or []
    if not isinstance(related_urls, list):
        related_urls = []

    images = entry.get("images") or []
    if not isinstance(images, list):
        images = []

    normalized_related_urls = []
    for item in related_urls:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        normalized_related_urls.append({"title": title, "url": url})

    normalized_images = []
    for item in images:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not url:
            continue

        if _looks_like_image_url(url):
            normalized_images.append({"title": title, "url": url})
        else:
            # If an item was mistakenly saved under images, show it as a normal link.
            normalized_related_urls.append({"title": title, "url": url})

    return {
        "explanation": str(entry.get("explanation") or ""),
        "example": str(entry.get("example") or ""),
        "analogy": str(entry.get("analogy") or ""),
        "extra_fields": [
            {
                "label": str(item.get("label") or "").strip(),
                "value": str(item.get("value") or "").strip(),
            }
            for item in extra_fields
            if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("value") or "").strip()
        ],
        "related_urls": [
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
            for item in normalized_related_urls
            if isinstance(item, dict) and str(item.get("url") or "").strip()
        ],
        "images": [
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
            for item in normalized_images
            if isinstance(item, dict) and str(item.get("url") or "").strip()
        ],
    }


def save_text_content(topic_slug, explanation, example, analogy, extra_fields=None, related_urls=None, images=None):
    all_content = _load_all()

    cleaned_extra_fields = []
    for item in (extra_fields or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if label and value:
            cleaned_extra_fields.append({"label": label, "value": value})

    cleaned_related_urls = []
    for item in (related_urls or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if url:
            cleaned_related_urls.append({"title": title, "url": url})

    cleaned_images = []
    for item in (images or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not url:
            continue

        if _looks_like_image_url(url):
            cleaned_images.append({"title": title, "url": url})
        else:
            cleaned_related_urls.append({"title": title, "url": url})

    all_content[topic_slug] = {
        "explanation": str(explanation or "").strip(),
        "example": str(example or "").strip(),
        "analogy": str(analogy or "").strip(),
        "extra_fields": cleaned_extra_fields,
        "related_urls": cleaned_related_urls,
        "images": cleaned_images,
    }
    _save_all(all_content)
