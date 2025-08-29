import os
from typing import Optional
import psycopg


def get_conn():
    dsn = os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@db:5432/aoidb")
    return psycopg.connect(dsn)


def ensure_source(cur, name: str, url: Optional[str] = None, type_: Optional[str] = None) -> int:
    cur.execute("SELECT id FROM sources WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO sources(name, url, type) VALUES(%s,%s,%s) RETURNING id",
        (name, url, type_),
    )
    return cur.fetchone()[0]


def insert_event(
    cur,
    source_id: int,
    title: str,
    body: Optional[str],
    event_type: str,
    occurred_at: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
    jurisdiction: Optional[str],
    confidence: Optional[float],
    severity: Optional[float],
) -> int:
    geom_wkt = None
    if lat is not None and lon is not None:
        geom_wkt = f"POINT({lon} {lat})"
    if geom_wkt:
        cur.execute(
            """
            INSERT INTO events
              (source_id, title, body, event_type, occurred_at, detected_at, geom, jurisdiction, confidence, severity)
            VALUES
              (%s,%s,%s,%s::event_type,%s, now(), ST_GeogFromText(%s), %s, %s, %s)
            RETURNING id
            """,
            (source_id, title, body, event_type, occurred_at, geom_wkt, jurisdiction, confidence, severity),
        )
    else:
        cur.execute(
            """
            INSERT INTO events
              (source_id, title, body, event_type, occurred_at, detected_at, jurisdiction, confidence, severity)
            VALUES
              (%s,%s,%s,%s::event_type,%s, now(), %s, %s, %s)
            RETURNING id
            """,
            (source_id, title, body, event_type, occurred_at, jurisdiction, confidence, severity),
        )
    return cur.fetchone()[0]

