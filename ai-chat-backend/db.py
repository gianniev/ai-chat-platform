import time
from typing import Optional

import psycopg2
from fastapi import HTTPException

from settings import DATABASE_URL


def get_connection():
    last_error = None

    for _ in range(10):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as error:
            last_error = error
            print("Postgres todavia no esta listo, reintentando...")
            time.sleep(2)

    raise last_error


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_message TEXT NOT NULL,
            assistant_message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'Nueva conversacion',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
            content TEXT NOT NULL,
            model TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            latency_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message_feedback (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS anonymous_chat_metrics (
            id SERIAL PRIMARY KEY,
            mode TEXT NOT NULL DEFAULT 'demo',
            provider TEXT,
            requested_provider TEXT,
            actual_provider TEXT,
            fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
            model TEXT,
            tokens_in_est INTEGER,
            tokens_out_est INTEGER,
            latency_ms INTEGER,
            persisted BOOLEAN NOT NULL DEFAULT FALSE,
            success BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS anonymous_feedback (
            id SERIAL PRIMARY KEY,
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            client_message_id TEXT,
            client_thread_id TEXT,
            model TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        ALTER TABLE anonymous_chat_metrics
        ADD COLUMN IF NOT EXISTS provider TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE anonymous_chat_metrics
        ADD COLUMN IF NOT EXISTS model TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE anonymous_chat_metrics
        ADD COLUMN IF NOT EXISTS requested_provider TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE anonymous_chat_metrics
        ADD COLUMN IF NOT EXISTS actual_provider TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE anonymous_chat_metrics
        ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
        ON conversations(user_id, updated_at DESC);
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_created
        ON chat_messages(conversation_id, created_at);
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_anonymous_chat_metrics_created
        ON anonymous_chat_metrics(created_at DESC);
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_anonymous_feedback_created
        ON anonymous_feedback(created_at DESC);
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def get_or_create_default_user(cur) -> int:
    cur.execute("SELECT id FROM users WHERE email = %s", ("guest@local",))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO users (email, name)
        VALUES (%s, %s)
        RETURNING id
        """,
        ("guest@local", "Invitado"),
    )
    return cur.fetchone()[0]


def resolve_user_id(cur, user_id: Optional[int]) -> int:
    if user_id is None:
        return get_or_create_default_user(cur)

    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return row[0]


def create_conversation(cur, user_id: int, title: str) -> int:
    cur.execute(
        """
        INSERT INTO conversations (user_id, title)
        VALUES (%s, %s)
        RETURNING id
        """,
        (user_id, title),
    )
    return cur.fetchone()[0]


def touch_conversation(cur, conversation_id: int):
    cur.execute(
        """
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (conversation_id,),
    )


def assert_conversation_owner(cur, conversation_id: int, user_id: int):
    cur.execute(
        "SELECT id, user_id FROM conversations WHERE id = %s",
        (conversation_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    if row[1] != user_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta conversacion.")


def load_recent_db_history(cur, conversation_id: int, limit: int):
    cur.execute(
        """
        SELECT role, content
        FROM chat_messages
        WHERE conversation_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (conversation_id, limit),
    )

    rows = cur.fetchall()
    rows.reverse()
    return [{"role": row[0], "content": row[1]} for row in rows]


def insert_chat_message(
    cur,
    conversation_id: int,
    role: str,
    content: str,
    model: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    latency_ms: Optional[int] = None,
):
    cur.execute(
        """
        INSERT INTO chat_messages (
            conversation_id,
            role,
            content,
            model,
            tokens_in,
            tokens_out,
            latency_ms
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (conversation_id, role, content, model, tokens_in, tokens_out, latency_ms),
    )
    return cur.fetchone()[0]


def insert_anonymous_chat_metric(
    mode: str,
    model: Optional[str],
    tokens_in_est: Optional[int],
    tokens_out_est: Optional[int],
    latency_ms: Optional[int],
    persisted: bool,
    success: bool = True,
    provider: Optional[str] = None,
    requested_provider: Optional[str] = None,
    actual_provider: Optional[str] = None,
    fallback_used: bool = False,
):
    actual_provider = actual_provider or provider
    requested_provider = requested_provider or provider
    safe_provider = actual_provider or "unknown"
    safe_model = model or "default"
    print(
        "analytics_insert_start "
        f"provider={safe_provider} model={safe_model} "
        f"latency_ms={latency_ms} persisted={persisted} fallback_used={fallback_used}",
        flush=True,
    )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO anonymous_chat_metrics (
                mode,
                provider,
                requested_provider,
                actual_provider,
                fallback_used,
                model,
                tokens_in_est,
                tokens_out_est,
                latency_ms,
                persisted,
                success
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                mode,
                actual_provider,
                requested_provider,
                actual_provider,
                fallback_used,
                model,
                tokens_in_est,
                tokens_out_est,
                latency_ms,
                persisted,
                success,
            ),
        )
        conn.commit()
        print(
            "analytics_insert_ok "
            f"provider={safe_provider} model={safe_model} "
            f"latency_ms={latency_ms} persisted={persisted} fallback_used={fallback_used}",
            flush=True,
        )
    except Exception as error:
        conn.rollback()
        print(
            "analytics_insert_failed "
            f"provider={safe_provider} model={safe_model} "
            f"error_type={type(error).__name__}",
            flush=True,
        )
        raise
    finally:
        cur.close()
        conn.close()


def insert_anonymous_feedback(
    rating: str,
    client_message_id: Optional[str],
    client_thread_id: Optional[str],
    model: Optional[str],
    comment: Optional[str],
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO anonymous_feedback (
                rating,
                client_message_id,
                client_thread_id,
                model,
                comment
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (rating, client_message_id, client_thread_id, model, comment),
        )
        feedback_id = cur.fetchone()[0]
        conn.commit()
        return feedback_id
    finally:
        cur.close()
        conn.close()
