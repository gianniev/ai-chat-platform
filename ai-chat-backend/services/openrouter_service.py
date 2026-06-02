import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from settings import OPENROUTER_API_KEY, OPENROUTER_DEFAULT_MODEL, SYSTEM_PROMPT

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterServiceError(RuntimeError):
    pass


def resolve_openrouter_model(model: Optional[str]) -> str:
    return (model or OPENROUTER_DEFAULT_MODEL or "deepseek/deepseek-chat-v3-0324:free").strip()


def build_openrouter_messages(history_messages: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in history_messages:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            messages.append({"role": role, "content": content})
    return messages


def generate_openrouter_response(history_messages: list[dict], model: Optional[str] = None):
    if not OPENROUTER_API_KEY:
        raise OpenRouterServiceError("OpenRouter API key is not configured.")

    selected_model = resolve_openrouter_model(model)
    payload = {
        "model": selected_model,
        "messages": build_openrouter_messages(history_messages),
    }

    request = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started_at = time.time()
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise OpenRouterServiceError(f"OpenRouter API request failed with status {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise OpenRouterServiceError("OpenRouter API request failed.") from exc
    except json.JSONDecodeError as exc:
        raise OpenRouterServiceError("OpenRouter API returned an invalid response.") from exc

    latency_ms = int((time.time() - started_at) * 1000)

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterServiceError("OpenRouter API response did not include text content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterServiceError("OpenRouter API response was empty.")

    return content.strip(), latency_ms, selected_model
