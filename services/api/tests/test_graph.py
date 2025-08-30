import os
import time

import psycopg
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def db_conn():
    dsn = "postgresql://aoidb:aoidb@localhost/aoidb"
    try:
        conn = psycopg.connect(dsn)
    except Exception:
        pytest.skip("postgres not available")
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS event_entities")
        cur.execute("DROP TABLE IF EXISTS events")
        cur.execute("DROP TABLE IF EXISTS entities")
        cur.execute("DROP TABLE IF EXISTS sources")
        cur.execute("CREATE TABLE sources(id serial PRIMARY KEY, name text)")
        cur.execute(
            "CREATE TABLE events(id serial PRIMARY KEY, source_id int references sources(id), title text, event_type text)"
        )
        cur.execute("CREATE TABLE entities(id serial PRIMARY KEY, type text, name text)")
        cur.execute(
            "CREATE TABLE event_entities(event_id int references events(id), entity_id int references entities(id), relation text, score float)"
        )
    conn.commit()
    os.environ["DATABASE_URL"] = dsn
    yield conn
    conn.close()


@pytest.fixture
def graph_client(db_conn):
    from app.main import app

    return TestClient(app)


def test_graph_two_hop(graph_client, db_conn):
    with db_conn.cursor() as cur:
        cur.execute("INSERT INTO sources(name) VALUES('src') RETURNING id")
        src = cur.fetchone()[0]
        cur.execute("INSERT INTO entities(type, name) VALUES('Org','Org1') RETURNING id")
        org = cur.fetchone()[0]
        cur.execute("INSERT INTO entities(type, name) VALUES('Person','Alice') RETURNING id")
        alice = cur.fetchone()[0]
        cur.execute("INSERT INTO entities(type, name) VALUES('Person','Bob') RETURNING id")
        bob = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO events(source_id, title, event_type) VALUES(%s,'E1','t') RETURNING id",
            (src,),
        )
        e1 = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO events(source_id, title, event_type) VALUES(%s,'E2','t') RETURNING id",
            (src,),
        )
        e2 = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO events(source_id, title, event_type) VALUES(%s,'E3','t') RETURNING id",
            (src,),
        )
        e3 = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO event_entities(event_id, entity_id, relation, score) VALUES (%s,%s,'mentioned',1.0)",
            [
                (e1, org),
                (e1, alice),
                (e2, org),
                (e2, alice),
                (e2, bob),
                (e3, org),
                (e3, bob),
            ],
        )
    db_conn.commit()

    r = graph_client.get(f"/graph?entity_id={org}&max=200")
    assert r.status_code == 200
    data = r.json()
    nodes = data["nodes"]
    edges = data["edges"]
    assert len([n for n in nodes if n["kind"] == "event"]) == 3
    assert len([n for n in nodes if n["kind"] == "entity"]) == 3

    # entity-entity weights aggregated by co-occurrence
    ee_edges = [
        e
        for e in edges
        if any(n["id"] == e["source"] and n["kind"] == "entity" for n in nodes)
        and any(n["id"] == e["target"] and n["kind"] == "entity" for n in nodes)
    ]

    def weight(a, b):
        for e in ee_edges:
            if (e["source"] == a and e["target"] == b) or (e["source"] == b and e["target"] == a):
                return e["weight"]
        return 0

    assert weight(org, alice) == 2
    assert weight(org, bob) == 2
    assert weight(alice, bob) == 1
    assert len(edges) == 10

    durations = []
    for _ in range(20):
        start = time.perf_counter()
        graph_client.get(f"/graph?entity_id={org}&max=200")
        durations.append(time.perf_counter() - start)
    durations.sort()
    idx = int(len(durations) * 0.95) - 1
    p95 = durations[idx]
    assert p95 < 0.2
