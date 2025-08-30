from uuid import uuid4, UUID
from datetime import datetime, timezone
import json

import services.api.app.main as m


def test_notebook_export_formats(client, monkeypatch):
    nb_id = UUID("11111111-1111-4111-8111-111111111111")
    ev_id = UUID("22222222-2222-4222-8222-222222222222")
    en_id = UUID("33333333-3333-4333-8333-333333333333")
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event_time = datetime(2024, 1, 2, 8, 30, 0, tzinfo=timezone.utc)

    def fake_fetch_one(sql, params=()):
        s = " ".join(sql.split()).lower()
        if s.startswith("select id, created_by, title, created_at from notebooks"):
            return {
                "id": nb_id,
                "created_by": "anonymous",
                "title": "My Notebook",
                "created_at": created_at,
            }
        if "from events" in s:
            return {
                "id": ev_id,
                "title": "Event Alpha",
                "time": event_time,
                "source_url": "https://example.com/src",
            }
        if "from entities" in s:
            return {"id": en_id, "type": "Org", "name": "ACME"}
        return None

    def fake_fetch_all(sql, params=()):
        s = " ".join(sql.split()).lower()
        if s.startswith("select id, kind, ref_id, note, created_at from notebook_items"):
            return [
                {
                    "id": uuid4(),
                    "notebook_id": nb_id,
                    "kind": "event",
                    "ref_id": ev_id,
                    "note": "first",
                    "created_at": created_at,
                },
                {
                    "id": uuid4(),
                    "notebook_id": nb_id,
                    "kind": "entity",
                    "ref_id": en_id,
                    "note": None,
                    "created_at": created_at,
                },
            ]
        return []

    monkeypatch.setattr(m, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    r = client.get(f"/notebooks/{nb_id}/export?fmt=json")
    assert r.status_code == 200
    with open("tests/api/golden/notebook_export.json", "r", encoding="utf-8") as f:
        assert r.json() == json.load(f)

    r = client.get(f"/notebooks/{nb_id}/export?fmt=md")
    assert r.status_code == 200
    with open("tests/api/golden/notebook_export.md", "r", encoding="utf-8") as f:
        assert r.text == f.read()

    r = client.get(f"/notebooks/{nb_id}/export?fmt=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
