"""
GET /api/v1/admin/dashboard-stats
===================================
Aggregated KPIs for the PHP admin dashboard (Task 17/19: evaluation +
reporting). The PHP admin app can either call this endpoint directly
(server-side cURL) or query MySQL itself -- both are supported since
admin-php ships its own PDO queries too. This endpoint is handy when
the admin panel is hosted on a different box than the DB.

NOTE: In production, protect this route (e.g. shared-secret header or
place FastAPI + MySQL on a private network only reachable by the PHP
backend) -- see docs/DEPLOYMENT.md.
"""

from fastapi import APIRouter, Depends, Query
from mysql.connector.pooling import PooledMySQLConnection

from app.db import get_connection
from app.models import DashboardStats

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard-stats", response_model=DashboardStats)
def dashboard_stats(days: int = Query(7, ge=1, le=90), conn: PooledMySQLConnection = Depends(get_connection)):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(DISTINCT session_id), COUNT(*),
               SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END)
        FROM chat_logs
        WHERE sender_type = 'bot' AND timestamp >= (NOW() - INTERVAL %s DAY)
        """,
        (days,),
    )
    total_conversations, total_messages, fallback_count = cursor.fetchone()
    total_messages = total_messages or 0
    fallback_count = fallback_count or 0
    fallback_rate = round((fallback_count / total_messages) * 100, 2) if total_messages else 0.0
    resolution_rate = round(100 - fallback_rate, 2) if total_messages else 0.0

    cursor.execute(
        """
        SELECT unanswered_query FROM kb_gap_log
        WHERE status != 'resolved'
        ORDER BY frequency DESC, flagged_at DESC
        LIMIT 5
        """
    )
    top_unanswered = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return DashboardStats(
        date_range_days=days,
        total_conversations=total_conversations or 0,
        total_messages=total_messages,
        fallback_rate=fallback_rate,
        resolution_rate=resolution_rate,
        top_unanswered=top_unanswered,
    )
