import json
import sqlite3
import uuid

from services.etl import fusion_worker


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("CREATE TABLE events(id TEXT PRIMARY KEY, title TEXT, raw TEXT)")
    conn.commit()
    return conn


def seed_events(conn):
    cur = conn.cursor()
    e1 = str(uuid.uuid4())
    raw1 = json.dumps({"summary": "John Smith attacked ACME Corp in Sydney"})
    cur.execute(
        "INSERT INTO events(id, title, raw) VALUES (?,?,?)",
        (e1, "ACME Corp breached", raw1),
    )
    e2 = str(uuid.uuid4())
    raw2 = json.dumps({"summary": "imo:9876543 vessel with mmsi:123456789"})
    cur.execute(
        "INSERT INTO events(id, title, raw) VALUES (?,?,?)",
        (e2, "Vessel report mmsi:123456789", raw2),
    )
    conn.commit()
    return e1, e2


def test_worker_creates_entities_and_edges():
    conn = make_conn()
    fusion_worker.ensure_schema(conn)
    seed_events(conn)
    processed = fusion_worker.process_unfused_events(conn)
    assert processed == 2

    cur = conn.cursor()
    cur.execute("SELECT kind, label FROM entities")
    entities = {(r["kind"], r["label"]) for r in cur.fetchall()}
    assert ("ORG", "ACME Corp") in entities
    assert ("PERSON", "John Smith") in entities
    assert ("GPE", "Sydney") in entities
    assert ("MMSI", "123456789") in entities
    assert ("IMO", "9876543") in entities

    cur.execute("SELECT COUNT(*) FROM event_entities")
    count = cur.fetchone()[0]
    assert count >= 5

    # Idempotent
    processed_again = fusion_worker.process_unfused_events(conn)
    assert processed_again == 0
    cur.execute("SELECT COUNT(*) FROM event_entities")
    assert cur.fetchone()[0] == count
