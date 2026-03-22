import requests

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL


DEFAULT_MODEL = OPENROUTER_MODEL
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _headers():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "AI LMS",
    }


def chat_completion(messages, model=DEFAULT_MODEL, max_tokens=None, temperature=None):
    payload = {
        "model": model,
        "messages": messages,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature

    response = requests.post(
        OPENROUTER_URL,
        headers=_headers(),
        json=payload,
        timeout=60,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            response.raise_for_status()
        raise RuntimeError(str(error_payload))

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return "\n".join(part for part in text_parts if part).strip()

    raise RuntimeError("OpenRouter returned an unexpected response format.")
