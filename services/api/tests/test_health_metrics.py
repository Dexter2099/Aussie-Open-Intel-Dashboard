from contextlib import contextmanager

import app.main as main
from fastapi.testclient import TestClient


def _ok_conn():
    @contextmanager
    def _conn():
        class Cur:
            def execute(self, sql):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

        class Conn:
            def cursor(self):
                return Cur()

            def close(self):
                pass

        yield Conn()

    return _conn()


class _RedisOK:
    def ping(self):
        return True


def test_healthz_ok(monkeypatch):
    monkeypatch.setattr(main, "get_conn", _ok_conn)
    monkeypatch.setattr(main.redis, "Redis", lambda *a, **k: _RedisOK())
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_healthz_db_failure(monkeypatch):
    @contextmanager
    def _bad_conn():
        raise Exception("db down")
        yield  # pragma: no cover

    monkeypatch.setattr(main, "get_conn", _bad_conn)
    monkeypatch.setattr(main.redis, "Redis", lambda *a, **k: _RedisOK())
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 500


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "request_total" in body
    assert "error_total" in body

