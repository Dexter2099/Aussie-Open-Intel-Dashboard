from datetime import datetime, timedelta, timezone

import app.main as m


def _seed_events():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "id": 1,
            "source_id": 1,
            "title": "Fire A",
            "body": None,
            "event_type": "Wildfire",
            "occurred_at": None,
            "detected_at": base,
            "jurisdiction": None,
            "confidence": None,
            "severity": None,
            "lon": 150.0,
            "lat": -30.0,
            "raw": {"a": 1},
        },
        {
            "id": 2,
            "source_id": 1,
            "title": "Storm B",
            "body": None,
            "event_type": "Weather",
            "occurred_at": None,
            "detected_at": base - timedelta(hours=1),
            "jurisdiction": None,
            "confidence": None,
            "severity": None,
            "lon": 150.2,
            "lat": -30.2,
            "raw": {"b": 2},
        },
        {
            "id": 3,
            "source_id": 1,
            "title": "Fire C",
            "body": None,
            "event_type": "Wildfire",
            "occurred_at": None,
            "detected_at": base - timedelta(hours=2),
            "jurisdiction": None,
            "confidence": None,
            "severity": None,
            "lon": 160.0,
            "lat": -20.0,
            "raw": {"c": 3},
        },
    ]


def test_events_filters(client, monkeypatch):
    events = _seed_events()

    def fake_fetch_all(sql, params=()):
        filtered = events
        idx = 0
        if "e.event_type = %s" in sql:
            typ = params[idx]
            idx += 1
            filtered = [e for e in filtered if e["event_type"] == typ]
        if "e.title ILIKE %s" in sql:
            term = params[idx].strip("% ").lower()
            idx += 1
            filtered = [e for e in filtered if term in e["title"].lower()]
        limit = params[-1]
        filtered = sorted(filtered, key=lambda r: (r["detected_at"], r["id"]), reverse=True)
        return [dict(e) for e in filtered[:limit]]

    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)
    r = client.get("/events?type=Wildfire&q=Fire&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert all(ev["event_type"] == "Wildfire" for ev in data["items"])


def test_events_bbox_filter(client, monkeypatch):
    events = _seed_events()

    def fake_fetch_all(sql, params=()):
        filtered = events
        idx = 0
        if "ST_Intersects" in sql or "ST_X" in sql:
            minlon, minlat, maxlon, maxlat = params[idx: idx + 4]
            idx += 4
            filtered = [
                e
                for e in filtered
                if e["lon"] is not None
                and minlon <= e["lon"] <= maxlon
                and minlat <= e["lat"] <= maxlat
            ]
        limit = params[-1]
        filtered = sorted(filtered, key=lambda r: (r["detected_at"], r["id"]), reverse=True)
        return [dict(e) for e in filtered[:limit]]

    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)
    r = client.get("/events?bbox=149.9,-30.1,150.1,-29.9&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 1


def test_events_cursor_pagination(client, monkeypatch):
    events = _seed_events()

    def fake_fetch_all(sql, params=()):
        filtered = sorted(events, key=lambda r: (r["detected_at"], r["id"]), reverse=True)
        idx = 0
        if "(e.detected_at, e.id) < (%s, %s)" in sql:
            cur_ts, cur_id = params[idx: idx + 2]
            idx += 2
            filtered = [e for e in filtered if (e["detected_at"], e["id"]) < (cur_ts, cur_id)]
        limit = params[-1]
        return [dict(e) for e in filtered[:limit]]

    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    r1 = client.get("/events?limit=1")
    assert r1.status_code == 200
    page1 = r1.json()
    assert len(page1["items"]) == 1
    cursor = page1["next_cursor"]

    r2 = client.get(f"/events?limit=1&cursor={cursor}")
    assert r2.status_code == 200
    page2 = r2.json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] != page1["items"][0]["id"]

