from typing import Optional

from fastapi import APIRouter, HTTPException

from db import assert_conversation_owner, create_conversation, get_connection, resolve_user_id
from schemas import CreateConversationRequest, UpdateConversationRequest

router = APIRouter()


@router.post("/conversations")
def create_new_conversation(request: CreateConversationRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = resolve_user_id(cur, request.user_id)
        title = (request.title or "Nueva conversacion").strip() or "Nueva conversacion"
        conversation_id = create_conversation(cur, user_id, title)
        conn.commit()
        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title,
        }
    finally:
        cur.close()
        conn.close()


@router.get("/conversations")
def list_conversations(user_id: Optional[int] = None, limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100.")

    conn = get_connection()
    cur = conn.cursor()

    try:
        resolved_user_id = resolve_user_id(cur, user_id)
        cur.execute(
            """
            SELECT id, title, status, created_at, updated_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (resolved_user_id, limit),
        )
        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    user_id: Optional[int] = None,
    limit: int = 50,
):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 200.")

    conn = get_connection()
    cur = conn.cursor()

    try:
        resolved_user_id = resolve_user_id(cur, user_id)
        assert_conversation_owner(cur, conversation_id, resolved_user_id)

        cur.execute(
            """
            SELECT id, role, content, model, tokens_in, tokens_out, latency_ms, created_at
            FROM chat_messages
            WHERE conversation_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (conversation_id, limit),
        )
        rows = cur.fetchall()
        rows.reverse()

        return [
            {
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "model": row[3],
                "tokens_in": row[4],
                "tokens_out": row[5],
                "latency_ms": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


@router.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: int, request: UpdateConversationRequest):
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="El titulo no puede estar vacio.")

    conn = get_connection()
    cur = conn.cursor()

    try:
        resolved_user_id = resolve_user_id(cur, request.user_id)
        assert_conversation_owner(cur, conversation_id, resolved_user_id)
        cur.execute(
            """
            UPDATE conversations
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, title, status, created_at, updated_at
            """,
            (title, conversation_id),
        )
        row = cur.fetchone()
        conn.commit()

        return {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }
    finally:
        cur.close()
        conn.close()


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user_id: Optional[int] = None):
    conn = get_connection()
    cur = conn.cursor()

    try:
        resolved_user_id = resolve_user_id(cur, user_id)
        assert_conversation_owner(cur, conversation_id, resolved_user_id)
        cur.execute(
            """
            DELETE FROM conversations
            WHERE id = %s
            RETURNING id
            """,
            (conversation_id,),
        )
        deleted_id = cur.fetchone()[0]
        conn.commit()

        return {"id": deleted_id, "deleted": True}
    finally:
        cur.close()
        conn.close()
