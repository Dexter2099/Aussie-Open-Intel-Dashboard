import json
from pathlib import Path
from datetime import datetime
from uuid import UUID

import pytest

DATA_DIR = Path(__file__).parent / "data"
FIXED_NOW = datetime(2024, 1, 1, 0, 0, 0)
NOTEBOOK_ID = UUID("11111111-1111-1111-1111-111111111111")
ITEM_ID = UUID("22222222-2222-2222-2222-222222222222")
EVENT_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture(autouse=True)
def fixed_uuid(monkeypatch):
    from app import main as m
    ids = [UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), NOTEBOOK_ID, UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), ITEM_ID, UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")]
    def fake_uuid():
        return ids.pop(0) if ids else UUID("99999999-9999-9999-9999-999999999999")
    monkeypatch.setattr(m, "uuid4", fake_uuid)
    return ids


@pytest.fixture
def inmem_db(monkeypatch):
    from app import main as m
    state = {
        "notebooks": {},
        "items": {},
        "events": {
            str(EVENT_ID): {
                "id": str(EVENT_ID),
                "title": "Sample Event",
                "occurred_at": FIXED_NOW,
                "detected_at": datetime(2024, 1, 1, 1, 0, 0),
                "source_url": "http://example.com/event",
            }
        },
    }

    def fetch_one(sql, params=()):
        sql = " ".join(sql.strip().lower().split())
        if sql.startswith("insert into notebooks"):
            nb = {
                "id": params[0],
                "title": params[1],
                "created_by": params[2],
                "created_at": FIXED_NOW.isoformat(),
            }
            state["notebooks"][params[0]] = nb
            return nb
        if sql.startswith("insert into notebook_items"):
            item = {
                "id": params[0],
                "notebook_id": params[1],
                "kind": params[2],
                "ref_id": params[3],
                "note": params[4],
                "created_at": FIXED_NOW.isoformat(),
            }
            state["items"].setdefault(params[1], []).append(item)
            return item
        if sql.startswith("select id, title, created_by, created_at from notebooks"):
            nb = state["notebooks"].get(str(params[0]))
            if nb and nb["created_by"] == params[1]:
                return nb
            return None
        if sql.startswith("delete from notebooks"):
            if params[0] in state["notebooks"]:
                del state["notebooks"][params[0]]
                return {"id": params[0]}
            return None
        if sql.startswith("delete from notebook_items"):
            items = state["items"].get(params[1], [])
            for i, it in enumerate(items):
                if it["id"] == params[0]:
                    del items[i]
                    return {"id": params[0]}
            return None
        return None

    def fetch_all(sql, params=()):
        sql = " ".join(sql.strip().lower().split())
        if sql.startswith("select ni.id"):
            nb_id = params[0]
            rows = []
            for it in state["items"].get(nb_id, []):
                row = {
                    "id": it["id"],
                    "kind": it["kind"],
                    "ref_id": it["ref_id"],
                    "note": it["note"],
                    "created_at": FIXED_NOW.isoformat(),
                    "event_title": None,
                    "event_occurred_at": None,
                    "event_detected_at": None,
                    "source_url": None,
                    "entity_name": None,
                    "entity_type": None,
                }
                if it["kind"] == "event":
                    ev = state["events"][it["ref_id"]]
                    row.update({
                        "event_title": ev["title"],
                        "event_occurred_at": ev["occurred_at"].isoformat(),
                        "event_detected_at": ev["detected_at"].isoformat(),
                        "source_url": ev["source_url"],
                    })
                rows.append(row)
            return rows
        if sql.startswith("select id, title, created_by, created_at from notebooks where created_by="):
            return list(state["notebooks"].values())
        return []

    monkeypatch.setattr(m, "fetch_one", fetch_one)
    monkeypatch.setattr(m, "fetch_all", fetch_all)
    return state


def test_notebook_flow(client, inmem_db):
    r = client.post("/notebooks", json={"title": "My NB"})
    assert r.status_code == 200
    nb_id = r.json()["id"]

    r = client.post(
        f"/notebooks/{nb_id}/items",
        json={"kind": "event", "ref_id": str(EVENT_ID), "note": "Check this"},
    )
    assert r.status_code == 200

    r = client.get(f"/notebooks/{nb_id}/export?fmt=json")
    assert r.status_code == 200
    expected_json = json.loads((DATA_DIR / "notebook_export.json").read_text())
    assert r.json() == expected_json

    r = client.get(f"/notebooks/{nb_id}/export?fmt=md")
    assert r.status_code == 200
    expected_md = (DATA_DIR / "notebook_export.md").read_text()
    assert r.text.strip() == expected_md.strip()

    r = client.get(f"/notebooks/{nb_id}/export?fmt=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
