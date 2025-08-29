import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

INGEST_ROOT = os.path.join(ROOT, "ingest")
if INGEST_ROOT not in sys.path:
    sys.path.insert(0, INGEST_ROOT)

from services.etl import fusion
from services.etl import nlp
from services.etl import enrich
from ingest.common import db


class FakeCursor:
    def __init__(self):
        self.executed = []
        self._id = 0

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "RETURNING id" in sql:
            self._id += 1

    def fetchone(self):
        if self.executed and "RETURNING id" in self.executed[-1][0]:
            return [self._id]
        return None


def test_extract_entities_and_relations():
    text = "John Smith works at ACME Corp in Sydney."
    entities, relations = fusion.process_event({"title": text, "body": ""})
    names = {(e["type"], e["name"]) for e in entities}
    assert ("Person", "John Smith") in names
    assert ("Org", "ACME Corp") in names
    assert ("Location", "Sydney") in names
    assert ("John Smith", "ACME Corp", "EMPLOYED_BY") in relations


def test_relation_db_writes():
    cur = FakeCursor()
    ent1 = {"type": "Person", "name": "John Smith"}
    ent2 = {"type": "Org", "name": "ACME Corp"}
    entities = [ent1, ent2]
    enrich.enrich_entities(entities)
    # Ensure entity insert and relation writes generate SQL
    e1_id = db.ensure_entity(cur, ent1["type"], ent1["name"], {})
    e2_id = db.ensure_entity(cur, ent2["type"], ent2["name"], {})
    db.link_event_entity(cur, 1, e1_id, "MENTIONS")
    db.link_event_entity(cur, 1, e2_id, "MENTIONS")
    db.upsert_relation(cur, e1_id, e2_id, "EMPLOYED_BY")
    sql = "\n".join(s for s, _ in cur.executed)
    assert "INSERT INTO event_entities" in sql
    assert "INSERT INTO relations" in sql
