import time

from huggingface_hub import InferenceClient

from schemas import ChatMessage
from settings import HISTORY_LIMIT, HF_TOKEN, MAX_TOKENS, MODEL_NAME, SYSTEM_PROMPT, TEMPERATURE

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


def generate_response(history_messages: list[dict]):
    started_at = time.time()

    response = hf_client.chat_completion(
        model=MODEL_NAME,
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


def iter_response_tokens(history_messages: list[dict]):
    started_at = time.time()
    stream = hf_client.chat_completion(
        model=MODEL_NAME,
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
