from fastapi import APIRouter, HTTPException

from db import get_connection

router = APIRouter()


@router.get("/")
def root():
    return {"status": "ok", "service": "ai-chat-backend"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "ai-chat-backend"}


@router.get("/health/db")
def database_health():
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "unavailable"},
        ) from exc
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
