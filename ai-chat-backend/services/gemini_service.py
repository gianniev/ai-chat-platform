import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from settings import GEMINI_API_KEY, GEMINI_DEFAULT_MODEL, SYSTEM_PROMPT
from services.provider_errors import ProviderServiceError

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


class GeminiServiceError(ProviderServiceError):
    pass


def resolve_gemini_model(model: Optional[str]) -> str:
    return (model or GEMINI_DEFAULT_MODEL or "gemini-2.5-flash").strip()


def build_gemini_contents(history_messages: list[dict]) -> list[dict]:
    contents = []
    for message in history_messages:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant":
            gemini_role = "model"
        elif role == "user":
            gemini_role = "user"
        else:
            continue
        contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return contents


def extract_gemini_text(data: dict) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    if not isinstance(parts, list):
        return ""

    chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "".join(chunks).strip()


def generate_gemini_response(history_messages: list[dict], model: Optional[str] = None):
    if not GEMINI_API_KEY:
        raise GeminiServiceError("Gemini API key is not configured.", retryable=False)

    selected_model = resolve_gemini_model(model)
    api_key = quote(GEMINI_API_KEY, safe="")
    model_path = quote(selected_model, safe="")
    url = GEMINI_URL_TEMPLATE.format(model=model_path, api_key=api_key)
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": build_gemini_contents(history_messages),
    }

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = time.time()
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        retryable = exc.code == 429 or exc.code >= 500
        raise GeminiServiceError(
            f"Gemini API request failed with status {exc.code}.",
            status_code=exc.code,
            retryable=retryable,
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise GeminiServiceError("Gemini API request timed out or failed.", retryable=True) from exc
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini API returned an invalid response.", retryable=False) from exc

    latency_ms = int((time.time() - started_at) * 1000)
    content = extract_gemini_text(data)
    if not content:
        raise GeminiServiceError("Gemini API response did not include text content.", retryable=False)

    return content, latency_ms, selected_model
