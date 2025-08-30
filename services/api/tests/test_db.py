import os
import uuid
from datetime import datetime
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def db_conn():
    dsn = "postgresql://aoidb:aoidb@localhost/aoidb"
    try:
        conn = psycopg.connect(dsn)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL server not available")
    migrations = ROOT / "db" / "migrations"
    with conn.cursor() as cur:
        for path in sorted(migrations.glob("*.sql")):
            cur.execute(path.read_text())
    conn.commit()
    os.environ["DATABASE_URL"] = dsn
    yield conn
    conn.close()


def test_upsert_event(db_conn):
    from db.events import upsert_event
    from db import fetch_one

    event_id = uuid.uuid4()
    upsert_event(
        id=event_id,
        type="cyber",
        title="Unit Test",
        time=datetime(2024, 1, 1, 0, 0, 0),
        lon=150.0,
        lat=-33.0,
        entities=[{"name": "foo"}],
        source="test",
        raw={"a": 1},
    )

    row = fetch_one("SELECT id, type, source FROM events WHERE id=%s", (event_id,))
    assert row["type"] == "cyber"
    assert row["source"] == "test"
