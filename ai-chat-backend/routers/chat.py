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
from settings import HISTORY_LIMIT

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def sse_token(token: str) -> str:
    return f"data: {json.dumps({'token': token})}\n\n"


def persist_or_record_response(
    history_messages: list[dict],
    full_response: str,
    latency_ms: int,
    persisted: bool,
    provider: str,
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
            provider=provider,
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
    provider: str,
    model: str,
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
                provider=provider,
                model=model,
                conversation_id=conversation_id,
                user_message=user_message,
            )
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
            provider=provider,
            model=model,
            conversation_id=conversation_id,
            user_message=user_message,
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


def build_precomputed_response_if_needed(provider: str, history_messages: list[dict], model: str):
    if provider == "huggingface":
        return None, model

    try:
        response_text, latency_ms, selected_model = generate_provider_response(
            provider=provider,
            history_messages=history_messages,
            model=model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return (response_text, latency_ms), selected_model


@router.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="El campo 'message' es obligatorio.")

    try:
        provider = normalize_provider(request.provider)
        model = resolve_provider_model(provider, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request_history = normalize_history(request.history)

    if not request.persist:
        history_messages = ensure_latest_user_turn(request_history, user_message)
        precomputed_response, model = build_precomputed_response_if_needed(provider, history_messages, model)
        return stream_chat_response(
            history_messages=history_messages,
            persisted=False,
            provider=provider,
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

    precomputed_response, model = build_precomputed_response_if_needed(provider, history_messages, model)
    return stream_chat_response(
        history_messages=history_messages,
        persisted=True,
        provider=provider,
        model=model,
        conversation_id=conversation_id,
        user_message=user_message,
        precomputed_response=precomputed_response,
    )
