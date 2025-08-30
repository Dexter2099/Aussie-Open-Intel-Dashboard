import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prometheus_client import REGISTRY

# Clear any existing collectors to avoid duplicate metric registration during tests
for collector in list(REGISTRY._collector_to_names.keys()):
    REGISTRY.unregister(collector)

from services.api.app.main import app

@pytest.fixture
def client():
    return TestClient(app)
