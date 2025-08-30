import os
import json
from uuid import UUID
from datetime import datetime
from contextlib import contextmanager
from typing import Any

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


def upsert_event(
    *,
    id: UUID,
    type: str,
    title: str,
    time: datetime,
    lon: float | None = None,
    lat: float | None = None,
    entities: list | None = None,
    source: str | None = None,
    raw: Any | None = None,
) -> dict | None:
    """Insert or update an event using (source, title, time) uniqueness heuristic."""
    loc_sql = (
        "ST_SetSRID(ST_MakePoint(%s,%s),4326)" if lon is not None and lat is not None else "NULL"
    )
    sql = f"""
    INSERT INTO events (id, type, title, time, location, entities, source, raw)
    VALUES (%s, %s, %s, %s, {loc_sql}, %s::jsonb, %s, %s::jsonb)
    ON CONFLICT (source, title, time) DO UPDATE
    SET type = EXCLUDED.type,
        location = EXCLUDED.location,
        entities = EXCLUDED.entities,
        raw = EXCLUDED.raw
    RETURNING *
    """
    params = [id, type, title, time]
    if lon is not None and lat is not None:
        params.extend([lon, lat])
    params.extend([json.dumps(entities or []), source, json.dumps(raw or {})])
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.fetchone()
