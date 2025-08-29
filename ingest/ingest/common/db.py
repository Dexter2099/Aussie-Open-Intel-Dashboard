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


def ensure_entity(cur, type_: str, name: str, attrs: Optional[dict] = None) -> int:
    """Return the entity id for ``(type_, name)`` inserting if necessary."""

    cur.execute(
        "SELECT id FROM entities WHERE type=%s::entity_type AND name=%s",
        (type_, name),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """
        INSERT INTO entities(type, name, attrs)
        VALUES(%s::entity_type, %s, %s::jsonb)
        RETURNING id
        """,
        (type_, name, attrs or {}),
    )
    return cur.fetchone()[0]


def link_event_entity(cur, event_id: int, entity_id: int, relation: str, score: Optional[float] = None) -> None:
    """Create a link between an event and an entity."""

    cur.execute(
        """
        INSERT INTO event_entities(event_id, entity_id, relation, score)
        VALUES(%s,%s,%s,%s)
        ON CONFLICT (event_id, entity_id, relation) DO NOTHING
        """,
        (event_id, entity_id, relation, score),
    )


def upsert_relation(cur, src_entity: int, dst_entity: int, relation: str) -> None:
    """Upsert a relation between two entities."""

    cur.execute(
        """
        INSERT INTO relations(src_entity, dst_entity, relation, first_seen, last_seen)
        VALUES(%s,%s,%s, now(), now())
        ON CONFLICT (src_entity, dst_entity, relation)
        DO UPDATE SET last_seen = excluded.last_seen
        """,
        (src_entity, dst_entity, relation),
    )
