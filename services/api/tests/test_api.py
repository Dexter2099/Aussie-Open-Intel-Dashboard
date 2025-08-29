import os
import psycopg
from fastapi.testclient import TestClient
from app.main import app

# ensure tests use local PostgreSQL
os.environ.setdefault("DATABASE_URL", "postgresql://aoidb:aoidb@localhost:5432/aoidb")

client = TestClient(app)

def setup_module(_):
    """Insert a sample source and event for API tests."""
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sources (name) VALUES ('Test Source') RETURNING id")
            source_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO events (source_id, title, body, event_type, occurred_at, detected_at, geom)
                VALUES (%s, %s, %s, 'Other', now(), now(),
                        ST_GeogFromText('POINT(151 -33)')) RETURNING id
                """,
                (source_id, 'Test Event', 'Body'),
            )
            conn.commit()

def teardown_module(_):
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events")
            cur.execute("DELETE FROM sources")
            conn.commit()

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_recent_events():
    resp = client.get("/events/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["title"] == "Test Event" for r in data["results"])

def test_search():
    resp = client.get("/search", params={"q": "Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["title"] == "Test Event" for r in data["results"])

def test_events_geojson():
    resp = client.get("/events/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["features"][0]["properties"]["title"] == "Test Event"
