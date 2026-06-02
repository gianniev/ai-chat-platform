from fastapi import APIRouter, HTTPException

from db import get_connection

router = APIRouter()


@router.get("/messages")
def get_messages(limit: int = 20):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 200.")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT id, user_message, assistant_message, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "user_message": row[1],
                "assistant_message": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()
