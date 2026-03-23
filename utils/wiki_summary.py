from functools import lru_cache

import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError, WikipediaException


@lru_cache(maxsize=512)
def get_topic_summary(query: str, language: str = "en", sentences: int = 3) -> str:
    """Return a short Wikipedia summary for a query and language, or empty string on failure."""
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return ""

    try:
        wikipedia.set_lang(language)
        return wikipedia.summary(cleaned_query, sentences=sentences, auto_suggest=True)
    except DisambiguationError as exc:
        for option in exc.options[:5]:
            try:
                wikipedia.set_lang(language)
                return wikipedia.summary(option, sentences=sentences, auto_suggest=True)
            except (DisambiguationError, PageError, WikipediaException):
                continue
        return ""
    except (PageError, WikipediaException):
        return ""