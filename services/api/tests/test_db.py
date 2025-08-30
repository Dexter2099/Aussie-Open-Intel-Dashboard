import os
import uuid
from datetime import datetime
from pathlib import Path
import subprocess

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def db_conn():
    dsn = "postgresql://aoidb:aoidb@localhost/aoidb"
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn
    subprocess.run(["alembic", "upgrade", "0003"], cwd=ROOT, check=True, env=env)
    os.environ["DATABASE_URL"] = dsn
    conn = psycopg.connect(dsn)
    yield conn
    conn.close()


def test_upsert_event(db_conn):
    from app.db import upsert_event, fetch_one

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
