from uuid import UUID, uuid4
from datetime import datetime, timezone

import services.api.app.main as m


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def test_notebook_crud_endpoints(client, monkeypatch):
    nb_id = UUID("11111111-1111-4111-8111-111111111111")
    item_id = UUID("22222222-2222-4222-8222-222222222222")
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    calls = {"fetch_one": [], "fetch_all": []}

    def fake_fetch_one(sql, params=()):
        calls["fetch_one"].append({"sql": sql, "params": params})
        s = " ".join(sql.split()).lower()
        if s.startswith("insert into notebooks"):
            return {
                "id": nb_id,
                "created_by": "anonymous",
                "title": params[2],
                "created_at": created_at,
            }
        if s.startswith("delete from notebooks"):
            return {"id": nb_id}
        if s.startswith("insert into notebook_items"):
            return {
                "id": item_id,
                "notebook_id": params[1],
                "kind": params[2],
                "ref_id": params[3],
                "note": params[4],
                "created_at": created_at,
            }
        if s.startswith("delete from notebook_items"):
            return {"id": params[0]}
        return None

    def fake_fetch_all(sql, params=()):
        calls["fetch_all"].append({"sql": sql, "params": params})
        s = " ".join(sql.split()).lower()
        if s.startswith("select id, created_by, title, created_at from notebooks"):
            return [
                {
                    "id": nb_id,
                    "created_by": "anonymous",
                    "title": "My Notebook",
                    "created_at": created_at,
                }
            ]
        return []

    monkeypatch.setattr(m, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(m, "fetch_all", fake_fetch_all)

    # Create notebook
    r = client.post("/notebooks", json={"title": "My Notebook"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(nb_id)
    assert data["title"] == "My Notebook"

    # List notebooks
    r = client.get("/notebooks")
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list) and lst[0]["id"] == str(nb_id)

    # Add item
    r = client.post(
        f"/notebooks/{nb_id}/items",
        json={"kind": "event", "ref_id": str(uuid4()), "note": "first"},
    )
    assert r.status_code == 200
    item = r.json()
    assert item["id"] == str(item_id)

    # Delete item
    r = client.delete(f"/notebooks/{nb_id}/items/{item_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(item_id)

    # Delete notebook
    r = client.delete(f"/notebooks/{nb_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(nb_id)

    # Ensure expected SQL executed
    assert any("insert into notebooks" in call["sql"].lower() for call in calls["fetch_one"])
    assert any("delete from notebooks" in call["sql"].lower() for call in calls["fetch_one"])
