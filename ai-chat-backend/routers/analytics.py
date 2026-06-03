from fastapi import APIRouter, HTTPException

from db import get_connection, insert_anonymous_feedback
from schemas import FeedbackRequest

router = APIRouter()


@router.post("/feedback")
def create_feedback(request: FeedbackRequest):
    rating = request.rating.strip().lower()
    if rating not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="rating debe ser 'up' o 'down'.")

    feedback_id = insert_anonymous_feedback(
        rating=rating,
        client_message_id=request.client_message_id,
        client_thread_id=request.client_thread_id,
        model=request.model,
        comment=request.comment,
    )

    return {"id": feedback_id, "stored": True}


@router.get("/analytics/summary")
def get_analytics_summary():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total_responses,
                COALESCE(ROUND(AVG(latency_ms)), 0) AS avg_latency_ms,
                COALESCE(SUM(tokens_in_est), 0) AS tokens_in_est,
                COALESCE(SUM(tokens_out_est), 0) AS tokens_out_est
            FROM anonymous_chat_metrics
            """
        )
        metrics = cur.fetchone()

        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE rating = 'up') AS positive_feedback,
                COUNT(*) FILTER (WHERE rating = 'down') AS negative_feedback
            FROM anonymous_feedback
            """
        )
        feedback = cur.fetchone()

        return {
            "total_responses": metrics[0],
            "avg_latency_ms": metrics[1],
            "tokens_in_est": metrics[2],
            "tokens_out_est": metrics[3],
            "positive_feedback": feedback[0],
            "negative_feedback": feedback[1],
        }
    finally:
        cur.close()
        conn.close()


@router.get("/analytics/models")
def get_model_analytics():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                COALESCE(NULLIF(actual_provider, ''), NULLIF(provider, ''), 'huggingface') AS provider,
                COALESCE(NULLIF(model, ''), 'default') AS model,
                COUNT(*) AS total_requests,
                COALESCE(ROUND(AVG(latency_ms)), 0) AS avg_latency_ms
            FROM anonymous_chat_metrics
            GROUP BY
                COALESCE(NULLIF(actual_provider, ''), NULLIF(provider, ''), 'huggingface'),
                COALESCE(NULLIF(model, ''), 'default')
            ORDER BY total_requests DESC, provider ASC, model ASC
            """
        )
        rows = cur.fetchall()
        return {
            "models": [
                {
                    "provider": row[0],
                    "model": row[1],
                    "total_requests": row[2],
                    "avg_latency_ms": row[3],
                }
                for row in rows
            ]
        }
    finally:
        cur.close()
        conn.close()


@router.get("/analytics/fallbacks")
def get_fallback_analytics():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total_requests,
                COUNT(*) FILTER (WHERE fallback_used IS TRUE) AS total_fallbacks
            FROM anonymous_chat_metrics
            """
        )
        total_requests, total_fallbacks = cur.fetchone()
        fallback_rate = float(total_fallbacks) / float(total_requests) if total_requests else 0.0
        return {
            "total_fallbacks": total_fallbacks,
            "fallback_rate": round(fallback_rate, 4),
        }
    finally:
        cur.close()
        conn.close()
