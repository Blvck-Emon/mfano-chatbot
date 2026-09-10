"""
Lightweight MySQL connection pooling for the FastAPI service.
Uses mysql-connector-python's built-in pool so we avoid pulling in a
full ORM (keeps the service lightweight, per project requirements).
"""

import mysql.connector
from mysql.connector import pooling

from app.config import settings

_pool: pooling.MySQLConnectionPool | None = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mfano_bora_pool",
            pool_size=5,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            autocommit=True,
        )
    return _pool


def get_connection():
    """FastAPI dependency: yields a pooled connection, always released."""
    conn = get_pool().get_connection()
    try:
        yield conn
    finally:
        conn.close()
