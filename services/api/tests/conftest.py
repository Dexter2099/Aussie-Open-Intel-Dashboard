from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Import app after potential monkeypatching if needed in tests
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_fetch_all(monkeypatch):
    called: Dict[str, Any] = {"calls": []}

    def _fake(sql: str, params: List | tuple = ()):  # type: ignore
        called["calls"].append({"sql": sql, "params": list(params)})
        # Default empty
        return []

    from app import main as m
    monkeypatch.setattr(m, "fetch_all", _fake)
    return called


@pytest.fixture
def mock_fetch_one(monkeypatch):
    called: Dict[str, Any] = {"calls": [], "result": None}

    def _fake(sql: str, params: List | tuple = ()):  # type: ignore
        called["calls"].append({"sql": sql, "params": list(params)})
        return called["result"]

    from app import main as m
    monkeypatch.setattr(m, "fetch_one", _fake)
    return called

