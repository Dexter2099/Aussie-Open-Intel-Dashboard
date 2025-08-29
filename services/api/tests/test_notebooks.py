import json
from datetime import datetime

def sample_nb():
    return {
        "id": 1,
        "owner": "anonymous",
        "title": "Test",
        "items": [{"event": 2}],
        "created_at": datetime.utcnow().isoformat()
    }

def test_notebook_crud(client, mock_fetch_one):
    mock_fetch_one["result"] = sample_nb()
    r = client.get("/notebooks/1")
    assert r.status_code == 200
    assert mock_fetch_one["calls"][0]["sql"].startswith("\n        SELECT")

    mock_fetch_one["result"] = sample_nb() | {"id": 2, "title": "New"}
    r = client.post("/notebooks", json={"title": "New", "items": []})
    assert r.status_code == 200
    assert mock_fetch_one["calls"][1]["sql"].strip().startswith("INSERT INTO notebooks")

    mock_fetch_one["result"] = sample_nb() | {"title": "Updated"}
    r = client.put("/notebooks/1", json={"title": "Updated", "items": [{"event": 2}]})
    assert r.status_code == 200
    assert mock_fetch_one["calls"][2]["sql"].strip().startswith("UPDATE notebooks")

def test_notebook_export(client, mock_fetch_one):
    nb = sample_nb()
    mock_fetch_one["result"] = nb
    r = client.get("/notebooks/1/export?fmt=md")
    assert r.status_code == 200
    assert r.text.startswith("# ")

    mock_fetch_one["result"] = nb
    r = client.get("/notebooks/1/export?fmt=json")
    assert r.status_code == 200
    assert r.json()["title"] == nb["title"]

    mock_fetch_one["result"] = nb
    r = client.get("/notebooks/1/export?fmt=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
