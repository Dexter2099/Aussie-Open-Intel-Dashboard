from datetime import datetime


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_auth_required_when_disallowed(monkeypatch):
    monkeypatch.setenv("ALLOW_ANON", "false")
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    import importlib
    import app.auth as auth
    importlib.reload(auth)
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient

    c = TestClient(main.app)
    # No token -> 401
    r = c.get("/health")
    assert r.status_code == 401

    # Obtain token via login endpoint
    t = c.post("/token", data={"username": "alice", "password": "pw"})
    assert t.status_code == 200
    token = t.json()["access_token"]

    # Valid token works
    r = c.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    # Invalid token -> 401
    r = c.get("/health", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401

    monkeypatch.setenv("ALLOW_ANON", "true")
    importlib.reload(auth)
    importlib.reload(main)


def test_token_endpoint(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "tokensecret")
    import importlib
    import app.auth as auth
    importlib.reload(auth)
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient

    c = TestClient(main.app)
    r = c.post("/token", data={"username": "bob", "password": "pw"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    decoded = auth.jwt.decode(token, "tokensecret", algorithms=[auth.ALGORITHM])
    assert decoded["sub"] == "bob"


def test_sources(client, mock_fetch_all):
    # Seed fetch_all to return a source
    def _return_sources(sql, params=()):
        return [{"id": 1, "name": "AU Wildfire Fixture", "type": "Wildfire"}]

    import app.main as m
    m.fetch_all = _return_sources  # type: ignore

    r = client.get("/sources")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["name"] == "AU Wildfire Fixture"


def test_events_recent_basic(client, mock_fetch_all):
    now = datetime.utcnow().isoformat()

    def _return_events(sql, params=()):
        return [
            {
                "id": 1,
                "source_id": 1,
                "source_name": "AU Wildfire Fixture",
                "title": "Grass fire near Toowoomba",
                "event_type": "Wildfire",
                "occurred_at": None,
                "detected_at": now,
                "jurisdiction": "QLD",
                "confidence": 0.8,
                "severity": 0.6,
                "lon": 151.95,
                "lat": -27.56,
            }
        ]

    import app.main as m
    m.fetch_all = _return_events  # type: ignore

    r = client.get("/events/recent?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source_name"] == "AU Wildfire Fixture"


def test_search_with_filters(client, mock_fetch_all):
    def _return_events(sql, params=()):
        # Ensure parameters reflect filters
        assert any(isinstance(p, str) and p.startswith("%fire%") for p in params)
        return []

    import app.main as m
    m.fetch_all = _return_events  # type: ignore

    r = client.get("/search?q=fire&limit=10&offset=0&sort=occurred_at")
    assert r.status_code == 200
    payload = r.json()
    assert payload["query"]["sort"] == "occurred_at"
    assert payload["query"]["limit"] == 10


def test_event_detail_with_geom(client, mock_fetch_one):
    now = datetime.utcnow().isoformat()
    mock_fetch_one["result"] = {
        "id": 123,
        "source_id": 1,
        "source_name": "AU Wildfire Fixture",
        "title": "Sample Event",
        "event_type": "Wildfire",
        "occurred_at": None,
        "detected_at": now,
        "jurisdiction": None,
        "confidence": 0.7,
        "severity": 0.4,
        "lon": 151.0,
        "lat": -27.0,
        "geom_wkt": "POINT(151 -27)",
    }

    r = client.get("/events/123?debug_geom=1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 123
    assert body["geom_wkt"].startswith("POINT(")


def test_events_geojson(client, mock_fetch_all):
    now = datetime.utcnow().isoformat()

    def _return_rows(sql, params=()):
        return [
            {
                "id": 1,
                "title": "Event 1",
                "body": None,
                "event_type": "Wildfire",
                "occurred_at": None,
                "detected_at": now,
                "lon": 150.1,
                "lat": -26.2,
                "jurisdiction": "QLD",
                "confidence": 0.5,
                "severity": 0.3,
                "source_name": "AU Wildfire Fixture",
            }
        ]

    import app.main as m
    m.fetch_all = _return_rows  # type: ignore

    r = client.get("/events/geojson?bbox=149,-28,152,-25")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert fc["count"] == 1
    assert fc["features"][0]["geometry"]["type"] == "Point"


def test_graph_entity_endpoint(client, mock_fetch_one, mock_fetch_all):
    mock_fetch_one["result"] = {"id": 1, "type": "Org", "name": "ACME"}
    r = client.get("/graph/entity/1")
    assert r.status_code == 200
    assert mock_fetch_one["calls"]


def test_graph_event_endpoint(client, mock_fetch_one, mock_fetch_all):
    mock_fetch_one["result"] = {"id": 1, "title": "Event"}
    r = client.get("/graph/event/1")
    assert r.status_code == 200
    assert mock_fetch_one["calls"]

