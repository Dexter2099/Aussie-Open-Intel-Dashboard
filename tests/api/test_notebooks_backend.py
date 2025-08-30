from datetime import datetime, timezone
from uuid import uuid4

import json

import services.api.app.main as m


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def test_notebooks_crud_and_export(client, monkeypatch, tmp_path):
    # IDs
    # Use fixed UUIDs for golden comparisons
    from uuid import UUID
    nb_id = UUID("11111111-1111-4111-8111-111111111111")
    ev_id = UUID("22222222-2222-4222-8222-222222222222")
    en_id = UUID("33333333-3333-4333-8333-333333333333")

    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event_time = datetime(2024, 1, 2, 8, 30, 0, tzinfo=timezone.utc)

    # Capture calls to route-level fetchers
    calls = {"fetch_one": [], "fetch_all": []}

    def fake_fetch_one(sql, params=()):
        calls["fetch_one"].append({"sql": sql, "params": params})
        s = " ".join(sql.split()).lower()
        if s.startswith("insert into notebooks"):
            return {"id": nb_id, "created_by": "anonymous", "title": params[2], "created_at": created_at}
        if s.startswith("insert into notebook_items"):
            # Return the inserted item
            return {
                "id": uuid4(),
                "notebook_id": params[1],
                "kind": params[2],
                "ref_id": params[3],
                "note": params[4],
                "created_at": created_at,
            }
        if s.startswith("select id, created_by, title, created_at from notebooks"):
            # Notebook lookup during export
            return {"id": nb_id, "created_by": "anonymous", "title": "My Notebook", "created_at": created_at}
        if "from events" in s:
            return {"id": ev_id, "title": "Event Alpha", "time": event_time, "source_url": "https://example.com/src"}
        if "from entities" in s:
            return {"id": en_id, "type": "Org", "name": "ACME"}
        return None

    def fake_fetch_all(sql, params=()):
        calls["fetch_all"].append({"sql": sql, "params": params})
        s = " ".join(sql.split()).lower()
        if s.startswith("select id, created_by, title, created_at from notebooks"):
            return [
                {"id": nb_id, "created_by": "anonymous", "title": "My Notebook", "created_at": created_at}
            ]
        if s.startswith("select id, kind, ref_id, note, created_at from notebook_items"):
            return [
                {"id": uuid4(), "notebook_id": nb_id, "kind": "event", "ref_id": ev_id, "note": "first", "created_at": created_at},
                {"id": uuid4(), "notebook_id": nb_id, "kind": "entity", "ref_id": en_id, "note": None, "created_at": created_at},
            ]
        return []

    monkeypatch.setattr(m, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    # Create notebook
    r = client.post("/notebooks", json={"title": "My Notebook"})
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "My Notebook"
    assert data["created_by"] == "anonymous"

    # Add items
    r = client.post(f"/notebooks/{nb_id}/items", json={"kind": "event", "ref_id": str(ev_id), "note": "first"})
    assert r.status_code == 200
    r = client.post(f"/notebooks/{nb_id}/items", json={"kind": "entity", "ref_id": str(en_id)})
    assert r.status_code == 200

    # Export JSON
    r = client.get(f"/notebooks/{nb_id}/export?fmt=json")
    assert r.status_code == 200
    json_payload = r.json()
    # Golden compare
    with open("tests/api/golden/notebook_export.json", "r", encoding="utf-8") as f:
        golden = json.load(f)
    assert json_payload == golden

    # Export Markdown
    r = client.get(f"/notebooks/{nb_id}/export?fmt=md")
    assert r.status_code == 200
    md_text = r.text
    with open("tests/api/golden/notebook_export.md", "r", encoding="utf-8") as f:
        md_golden = f.read()
    assert md_text == md_golden

    # Export PDF
    r = client.get(f"/notebooks/{nb_id}/export?fmt=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
