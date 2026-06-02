import time

from huggingface_hub import InferenceClient

from schemas import ChatMessage
from settings import HISTORY_LIMIT, HF_TOKEN, MAX_TOKENS, MODEL_NAME, SYSTEM_PROMPT, TEMPERATURE
from services.gemini_service import generate_gemini_response
from services.openrouter_service import generate_openrouter_response

hf_client = InferenceClient(api_key=HF_TOKEN)


def normalize_history(history: list[ChatMessage]):
    result = [
        {"role": msg.role, "content": msg.content}
        for msg in history
        if msg.role in {"user", "assistant"} and msg.content.strip()
    ]
    return result[-HISTORY_LIMIT:]


def ensure_latest_user_turn(history_messages: list[dict], user_message: str):
    if not history_messages or history_messages[-1]["role"] != "user":
        history_messages.append({"role": "user", "content": user_message})
    return history_messages


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def generate_response(history_messages: list[dict], model: str | None = None):
    started_at = time.time()

    response = hf_client.chat_completion(
        model=model or MODEL_NAME,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history_messages],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )

    latency_ms = int((time.time() - started_at) * 1000)
    assistant_message = response.choices[0].message.content
    return assistant_message, latency_ms


def extract_stream_token(chunk) -> str:
    try:
        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        content = getattr(delta, "content", None) if delta is not None else None
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        return content or ""
    except (AttributeError, IndexError, KeyError, TypeError):
        return ""


def iter_response_tokens(history_messages: list[dict], model: str | None = None):
    started_at = time.time()
    stream = hf_client.chat_completion(
        model=model or MODEL_NAME,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history_messages],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        stream=True,
    )

    for chunk in stream:
        token = extract_stream_token(chunk)
        if token:
            yield token

    latency_ms = int((time.time() - started_at) * 1000)
    return latency_ms


SUPPORTED_PROVIDERS = {"huggingface", "openrouter", "gemini"}


def normalize_provider(provider: str | None) -> str:
    selected_provider = (provider or "huggingface").strip().lower()
    if selected_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {selected_provider}")
    return selected_provider


def resolve_provider_model(provider: str, model: str | None = None) -> str:
    if provider == "huggingface":
        return (model or MODEL_NAME).strip()
    if provider == "openrouter":
        from services.openrouter_service import resolve_openrouter_model

        return resolve_openrouter_model(model)
    if provider == "gemini":
        from services.gemini_service import resolve_gemini_model

        return resolve_gemini_model(model)
    raise ValueError(f"Unsupported provider: {provider}")


def generate_provider_response(provider: str, history_messages: list[dict], model: str | None = None):
    selected_provider = normalize_provider(provider)
    if selected_provider == "huggingface":
        selected_model = resolve_provider_model("huggingface", model)
        response_text, latency_ms = generate_response(history_messages, model=selected_model)
        return response_text, latency_ms, selected_model
    if selected_provider == "openrouter":
        return generate_openrouter_response(history_messages, model=model)
    if selected_provider == "gemini":
        return generate_gemini_response(history_messages, model=model)
    raise ValueError(f"Unsupported provider: {selected_provider}")
