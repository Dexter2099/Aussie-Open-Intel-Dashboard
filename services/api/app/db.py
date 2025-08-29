import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row


def _dsn() -> str:
    return os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@db:5432/aoidb")


@contextmanager
def get_conn():
    conn = psycopg.connect(_dsn())
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple | list = ()):  # type: ignore
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def fetch_all(sql: str, params: tuple | list = ()):  # type: ignore
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

