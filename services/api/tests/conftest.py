from typing import Any, Dict, List
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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

