import os
import subprocess
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = ROOT / "infra" / "docker-compose.yml"

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")


def _compose_env() -> dict:
    env = os.environ.copy()
    env.update(
        {
            "POSTGRES_DB": "aoidb",
            "POSTGRES_USER": "aoidb",
            "POSTGRES_PASSWORD": "aoidb",
            "POSTGRES_PORT": "5432",
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6379",
            "API_PORT": "8000",
            "MINIO_ROOT_USER": "minioadmin",
            "MINIO_ROOT_PASSWORD": "minioadmin",
            "MINIO_BUCKET": "raw",
        }
    )
    return env


@pytest.fixture(scope="session")
def api_base_url():
    env = _compose_env()
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "db", "redis", "api"],
        check=True,
        env=env,
    )
    base = "http://localhost:8000"
    for _ in range(60):
        try:
            r = requests.get(base + "/health")
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("API did not become ready in time")

    ingest_env = env.copy()
    ingest_env["DATABASE_URL"] = "postgresql://aoidb:aoidb@localhost:5432/aoidb"
    subprocess.run([
        "python",
        "scripts/seed_sources.py",
    ], check=True, env=ingest_env)
    subprocess.run(
        ["python", "-m", "ingest.run", "--adapter", "au_wildfire_fixture"],
        check=True,
        env=ingest_env,
    )

    yield base

    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"],
        check=True,
        env=env,
    )


def test_sources(api_base_url):
    r = requests.get(f"{api_base_url}/sources")
    assert r.status_code == 200
    data = r.json()
    names = {src["name"] for src in data["results"]}
    expected = {
        "BOM Warnings",
        "QFES Incidents",
        "Police Media",
        "AIS Summary",
        "CERT/ACSC Advisories",
    }
    assert expected.issubset(names)


def test_search_and_detail(api_base_url):
    r = requests.get(f"{api_base_url}/search")
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) >= 2
    titles = {e["title"] for e in data["results"]}
    assert "Grass fire near Toowoomba" in titles
    event_id = data["results"][0]["id"]

    r2 = requests.get(f"{api_base_url}/events/{event_id}")
    assert r2.status_code == 200
    detail = r2.json()
    assert detail["id"] == event_id
    assert detail["title"]


def test_events_geojson(api_base_url):
    bbox = "149,-28,153,-25"
    r = requests.get(f"{api_base_url}/events/geojson?bbox={bbox}")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert fc["count"] >= 2
