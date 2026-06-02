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
    iter_response_tokens,
    normalize_history,
)
from settings import HISTORY_LIMIT, MODEL_NAME

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def sse_token(token: str) -> str:
    return f"data: {json.dumps({'token': token})}\n\n"


def stream_chat_response(
    history_messages: list[dict],
    persisted: bool,
    conversation_id: Optional[int] = None,
    user_message: Optional[str] = None,
    user_id: Optional[int] = None,
):
    def generate():
        started_at = time.time()
        full_response = ""

        for token in iter_response_tokens(history_messages):
            full_response += token
            yield sse_token(token)

        latency_ms = int((time.time() - started_at) * 1000)
        yield "data: [DONE]\n\n"

        prompt_text = " ".join(msg["content"] for msg in history_messages)
        tokens_in_est = estimate_tokens(prompt_text)
        tokens_out_est = estimate_tokens(full_response)

        if not persisted:
            insert_anonymous_chat_metric(
                mode="demo",
                model=MODEL_NAME,
                tokens_in_est=tokens_in_est,
                tokens_out_est=tokens_out_est,
                latency_ms=latency_ms,
                persisted=False,
            )
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
                model=MODEL_NAME,
                tokens_in=tokens_in_est,
                latency_ms=latency_ms,
            )

            insert_chat_message(
                cur,
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                model=MODEL_NAME,
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

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="El campo 'message' es obligatorio.")

    request_history = normalize_history(request.history)

    if not request.persist:
        history_messages = ensure_latest_user_turn(request_history, user_message)
        return stream_chat_response(history_messages=history_messages, persisted=False, user_id=request.user_id)

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

    return stream_chat_response(
        history_messages=history_messages,
        persisted=True,
        conversation_id=conversation_id,
        user_message=user_message,
        user_id=user_id,
    )
