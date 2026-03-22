from urllib.parse import quote

import requests

from config import WIKIPEDIA_SEARCH_LIMIT


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
REQUEST_HEADERS = {
    "User-Agent": "AI-LMS/1.0 (topic doubt assistant)",
}


def _search_titles(query, limit):
    response = requests.get(
        WIKIPEDIA_API_URL,
        headers=REQUEST_HEADERS,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("query", {}).get("search", [])
    return [item.get("title", "") for item in items if item.get("title")]


def _get_summary(title):
    response = requests.get(
        WIKIPEDIA_SUMMARY_URL.format(title=quote(title, safe="")),
        headers=REQUEST_HEADERS,
        timeout=20,
    )
    if response.status_code >= 400:
        return None

    data = response.json()
    extract = (data.get("extract") or "").strip()
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
    image_url = data.get("thumbnail", {}).get("source") or _get_page_image(title)

    if not extract or not page_url:
        return None

    return {
        "title": data.get("title") or title,
        "snippet": extract,
        "source_url": page_url,
        "image_url": image_url,
    }


def _get_page_image(title):
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            headers=REQUEST_HEADERS,
            params={
                "action": "query",
                "format": "json",
                "prop": "pageimages",
                "titles": title,
                "pithumbsize": 800,
                "pilicense": "any",
            },
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    pages = response.json().get("query", {}).get("pages", {})
    for page in pages.values():
        thumbnail = page.get("thumbnail", {})
        if thumbnail.get("source"):
            return thumbnail["source"]
    return None


def search_topic_resources(topic, question, limit=WIKIPEDIA_SEARCH_LIMIT):
    queries = [
        f"{topic.replace('_', ' ')} {question}",
        topic.replace("_", " "),
    ]
    seen_titles = set()
    results = []

    for query in queries:
        try:
            titles = _search_titles(query, limit)
        except requests.RequestException:
            continue

        for title in titles:
            normalized = title.lower().strip()
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)

            summary = _get_summary(title)
            if not summary:
                continue

            results.append(summary)
            if len(results) >= limit:
                return results

    return results
