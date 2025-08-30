import os
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row


def _dsn() -> str:
    """Return the database connection string."""
    return os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@db:5432/aoidb")


@contextmanager
def get_conn():
    """Yield a new psycopg connection."""
    conn = psycopg.connect(_dsn())
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple | list = ()):  # type: ignore
    """Fetch a single row as a dict."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def fetch_all(sql: str, params: tuple | list = ()):  # type: ignore
    """Fetch all rows as a list of dicts."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
