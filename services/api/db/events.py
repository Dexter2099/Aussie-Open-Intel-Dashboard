import json
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from . import get_conn


def upsert_event(
    *,
    id: UUID,
    type: str,
    title: str,
    time: datetime,
    lon: float | None = None,
    lat: float | None = None,
    entities: list | None = None,
    source: str,
    raw: Any,
) -> dict | None:
    """Insert or update an event using (source, title, time) uniqueness."""
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
