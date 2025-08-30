import json
import os
import re
import sqlite3
import time
import uuid
from typing import Iterable, Tuple

import spacy
from spacy.cli import download

MMSI_RE = re.compile(r"mmsi:(\d+)", re.IGNORECASE)
IMO_RE = re.compile(r"imo:(\d+)", re.IGNORECASE)


def _load_model():
    """Load spaCy model, downloading if missing."""
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        download("en_core_web_sm")
        return spacy.load("en_core_web_sm")


NLP = _load_model()


def get_conn(url: str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection using ``url`` or ``FUSION_DB`` env."""
    db_path = url or os.getenv("FUSION_DB", ":memory:")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure entity and event_entity tables exist."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS entities(
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            label TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(kind, label)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS event_entities(
            event_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            provenance TEXT NOT NULL,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(event_id, entity_id, provenance)
        )
        """
    )
    conn.commit()


def _extract_entities(text: str) -> Iterable[Tuple[str, str, str]]:
    """Yield (kind, label, provenance) tuples from ``text``."""
    doc = NLP(text)
    for ent in doc.ents:
        if ent.label_ in {"ORG", "PERSON", "GPE", "LOC"}:
            kind = {
                "ORG": "ORG",
                "PERSON": "PER",
                "GPE": "LOC",
                "LOC": "LOC",
            }[ent.label_]
            yield kind, ent.text, "ner"
    for m in MMSI_RE.finditer(text):
        yield "MMSI", m.group(1), "regex"
    for m in IMO_RE.finditer(text):
        yield "IMO", m.group(1), "regex"


def _upsert_entity(conn: sqlite3.Connection, kind: str, label: str) -> str:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM entities WHERE kind=? AND label=?",
        (kind, label),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    ent_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO entities(id, kind, label) VALUES(?,?,?)",
        (ent_id, kind, label),
    )
    conn.commit()
    return ent_id


def _link_event_entity(
    conn: sqlite3.Connection,
    event_id: str,
    entity_id: str,
    provenance: str,
    confidence: float,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO event_entities(event_id, entity_id, provenance, confidence)
        VALUES(?,?,?,?)
        """,
        (event_id, entity_id, provenance, confidence),
    )
    conn.commit()


def process_event(conn: sqlite3.Connection, event: sqlite3.Row) -> None:
    raw = event["raw"] or "{}"
    try:
        description = json.loads(raw).get("description", "")
    except Exception:
        description = ""
    text = f"{event['title']} {description}".strip()
    for kind, label, prov in _extract_entities(text):
        ent_id = _upsert_entity(conn, kind, label)
        confidence = 0.9 if prov == "regex" else 0.8
        _link_event_entity(conn, event["id"], ent_id, prov, confidence)


def process_unfused_events(conn: sqlite3.Connection) -> int:
    """Process unfused events in the database once."""
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.id, e.title, e.raw
        FROM events e
        LEFT JOIN event_entities ee ON e.id = ee.event_id
        WHERE ee.event_id IS NULL
        """
    )
    rows = cur.fetchall()
    for row in rows:
        process_event(conn, row)
    return len(rows)


def run() -> None:
    """Continuously poll for unfused events and process them."""
    conn = get_conn()
    ensure_schema(conn)
    while True:
        process_unfused_events(conn)
        time.sleep(10)


if __name__ == "__main__":
    run()
