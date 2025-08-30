from datetime import datetime, timezone
from uuid import uuid4

import services.api.app.main as m


def test_event_detail(client, monkeypatch):
    eid = uuid4()
    event_row = {
        "id": eid,
        "type": "bushfire",
        "title": "Event A",
        "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "lon": 150.0,
        "lat": -30.0,
        "source": "sensor",
        "raw": {"a": 1},
    }
    ent_rows = [
        {"id": uuid4(), "kind": "Person", "label": "Alice"},
        {"id": uuid4(), "kind": "Org", "label": "ACME"},
    ]

    def fake_fetch_one(sql, params=()):
        return event_row if params and params[0] == eid else None

    def fake_fetch_all(sql, params=()):
        return ent_rows if params and params[0] == eid else []

    monkeypatch.setattr(m, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    r = client.get(f"/events/{eid}", params={"include_raw": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(eid)
    assert data["location"]["coordinates"] == [150.0, -30.0]
    assert len(data["entities"]) == 2
    assert data["source"] == "sensor"
    assert data["raw"] == {"a": 1}


def test_entity_detail(client, monkeypatch):
    eid = uuid4()
    entity_row = {"id": eid, "kind": "Org", "label": "ACME"}
    event1 = {
        "id": uuid4(),
        "type": "bushfire",
        "title": "Event A",
        "time": datetime(2024, 1, 2, tzinfo=timezone.utc),
    }
    event2 = {
        "id": uuid4(),
        "type": "weather",
        "title": "Event B",
        "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    events = [event1, event2]

    def fake_fetch_one(sql, params=()):
        return entity_row if params and params[0] == eid else None

    def fake_fetch_all(sql, params=()):
        return events if params and params[0] == eid else []

    monkeypatch.setattr(m, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    r = client.get(f"/entities/{eid}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(eid)
    assert data["label"] == "ACME"
    assert [e["id"] for e in data["events"]] == [
        str(event1["id"]),
        str(event2["id"]),
    ]
