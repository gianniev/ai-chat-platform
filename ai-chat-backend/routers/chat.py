import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from db import (
    assert_conversation_owner,
    create_conversation,
    get_connection,
    insert_anonymous_chat_metric,
    insert_chat_message,
    load_recent_db_history,
    resolve_user_id,
    touch_conversation,
)
from schemas import ChatRequest
from services.chat_service import (
    ensure_latest_user_turn,
    estimate_tokens,
    generate_provider_response,
    iter_response_tokens,
    normalize_history,
    normalize_provider,
    resolve_provider_model,
)
from services.provider_errors import ProviderServiceError
from settings import HISTORY_LIMIT

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}

FALLBACK_ORDER = ["gemini", "openrouter", "huggingface"]


def sse_token(token: str) -> str:
    return f"data: {json.dumps({'token': token})}\n\n"


def sse_metadata(provider: str, model: str, latency_ms: int) -> str:
    return f"data: {json.dumps({'metadata': {'provider': provider, 'model': model, 'latency_ms': latency_ms}})}\n\n"


def get_fallback_candidates(requested_provider: str) -> list[str]:
    try:
        start_index = FALLBACK_ORDER.index(requested_provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {requested_provider}") from exc
    return FALLBACK_ORDER[start_index:]


def log_provider_event(event: str, **values):
    safe_values = " ".join(f"{key}={value}" for key, value in values.items() if value is not None)
    print(f"{event} {safe_values}".strip(), flush=True)


def persist_or_record_response(
    history_messages: list[dict],
    full_response: str,
    latency_ms: int,
    persisted: bool,
    requested_provider: str,
    actual_provider: str,
    fallback_used: bool,
    model: str,
    conversation_id: Optional[int] = None,
    user_message: Optional[str] = None,
):
    prompt_text = " ".join(msg["content"] for msg in history_messages)
    tokens_in_est = estimate_tokens(prompt_text)
    tokens_out_est = estimate_tokens(full_response)

    try:
        insert_anonymous_chat_metric(
            mode="demo",
            provider=actual_provider,
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            fallback_used=fallback_used,
            model=model,
            tokens_in_est=tokens_in_est,
            tokens_out_est=tokens_out_est,
            latency_ms=latency_ms,
            persisted=persisted,
        )
    except Exception:
        # The insert function already logs a sanitized failure. Do not break a successful chat response.
        pass

    if not persisted:
        return

    if conversation_id is None or user_message is None:
        return

    conn = get_connection()
    cur = conn.cursor()
    try:
        insert_chat_message(
            cur,
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            model=model,
            tokens_in=tokens_in_est,
            latency_ms=latency_ms,
        )

        insert_chat_message(
            cur,
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            model=model,
            tokens_in=tokens_in_est,
            tokens_out=tokens_out_est,
            latency_ms=latency_ms,
        )

        cur.execute(
            """
            INSERT INTO messages (user_message, assistant_message)
            VALUES (%s, %s)
            """,
            (user_message, full_response),
        )

        touch_conversation(cur, conversation_id)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def stream_chat_response(
    history_messages: list[dict],
    persisted: bool,
    requested_provider: str,
    actual_provider: str,
    model: str,
    fallback_used: bool,
    conversation_id: Optional[int] = None,
    user_message: Optional[str] = None,
    precomputed_response: Optional[tuple[str, int]] = None,
):
    def generate():
        if precomputed_response is not None:
            full_response, latency_ms = precomputed_response
            if full_response:
                yield sse_token(full_response)
            persist_or_record_response(
                history_messages=history_messages,
                full_response=full_response,
                latency_ms=latency_ms,
                persisted=persisted,
                requested_provider=requested_provider,
                actual_provider=actual_provider,
                fallback_used=fallback_used,
                model=model,
                conversation_id=conversation_id,
                user_message=user_message,
            )
            yield sse_metadata(provider=actual_provider, model=model, latency_ms=latency_ms)
            yield "data: [DONE]\n\n"
            return

        started_at = time.time()
        full_response = ""

        for token in iter_response_tokens(history_messages, model=model):
            full_response += token
            yield sse_token(token)

        latency_ms = int((time.time() - started_at) * 1000)
        persist_or_record_response(
            history_messages=history_messages,
            full_response=full_response,
            latency_ms=latency_ms,
            persisted=persisted,
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            fallback_used=fallback_used,
            model=model,
            conversation_id=conversation_id,
            user_message=user_message,
        )
        yield sse_metadata(provider=actual_provider, model=model, latency_ms=latency_ms)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


def build_precomputed_response_if_needed(requested_provider: str, history_messages: list[dict], requested_model: str):
    if requested_provider == "huggingface":
        return None, requested_provider, requested_model, False

    for candidate_provider in get_fallback_candidates(requested_provider):
        candidate_model = requested_model if candidate_provider == requested_provider else resolve_provider_model(candidate_provider, None)
        log_provider_event(
            "provider_fallback_attempt",
            requested_provider=requested_provider,
            candidate_provider=candidate_provider,
        )

        try:
            response_text, latency_ms, selected_model = generate_provider_response(
                provider=candidate_provider,
                history_messages=history_messages,
                model=candidate_model,
            )
        except ProviderServiceError as exc:
            log_provider_event(
                "provider_fallback_failed",
                requested_provider=requested_provider,
                candidate_provider=candidate_provider,
                status_code=exc.status_code,
                retryable=exc.retryable,
            )
            if not exc.retryable:
                break
            continue
        except RuntimeError:
            log_provider_event(
                "provider_fallback_failed",
                requested_provider=requested_provider,
                candidate_provider=candidate_provider,
                retryable=False,
            )
            break

        fallback_used = candidate_provider != requested_provider
        if fallback_used:
            log_provider_event(
                "provider_fallback_used",
                requested_provider=requested_provider,
                actual_provider=candidate_provider,
            )
        return (response_text, latency_ms), candidate_provider, selected_model, fallback_used

    raise HTTPException(
        status_code=502,
        detail="No se pudo generar una respuesta con los proveedores disponibles.",
    )


@router.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="El campo 'message' es obligatorio.")

    try:
        requested_provider = normalize_provider(request.provider)
        requested_model = resolve_provider_model(requested_provider, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request_history = normalize_history(request.history)

    if not request.persist:
        history_messages = ensure_latest_user_turn(request_history, user_message)
        precomputed_response, actual_provider, model, fallback_used = build_precomputed_response_if_needed(
            requested_provider, history_messages, requested_model
        )
        return stream_chat_response(
            history_messages=history_messages,
            persisted=False,
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            fallback_used=fallback_used,
            model=model,
            precomputed_response=precomputed_response,
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = resolve_user_id(cur, request.user_id)

        if request.conversation_id is not None:
            conversation_id = request.conversation_id
            assert_conversation_owner(cur, conversation_id, user_id)
        else:
            generated_title = user_message[:60].strip() or "Nueva conversacion"
            conversation_id = create_conversation(cur, user_id, generated_title)
            conn.commit()

        history_messages = request_history
        if not history_messages:
            history_messages = load_recent_db_history(cur, conversation_id, limit=HISTORY_LIMIT)
        history_messages = ensure_latest_user_turn(history_messages, user_message)
    finally:
        cur.close()
        conn.close()

    precomputed_response, actual_provider, model, fallback_used = build_precomputed_response_if_needed(
        requested_provider, history_messages, requested_model
    )
    return stream_chat_response(
        history_messages=history_messages,
        persisted=True,
        requested_provider=requested_provider,
        actual_provider=actual_provider,
        fallback_used=fallback_used,
        model=model,
        conversation_id=conversation_id,
        user_message=user_message,
        precomputed_response=precomputed_response,
    )
