import json
import pathlib
import sys
from datetime import datetime

BASE_PATH = pathlib.Path(__file__).resolve()
sys.path.append(str(BASE_PATH.parents[2]))
sys.path.append(str(BASE_PATH.parents[1]))

from ingest.common.schemas import RawPayload

import types

services = types.ModuleType("services")
etl = types.ModuleType("services.etl")
fusion = types.ModuleType("services.etl.fusion")
fusion.process_event = lambda data: ([], [])
etl.fusion = fusion
services.etl = etl
sys.modules.setdefault("services", services)
sys.modules.setdefault("services.etl", etl)
sys.modules.setdefault("services.etl.fusion", fusion)

from ingest import run
from ingest.adapters import (
    ais,
    bushfire_alerts,
    cyber_advisories,
    acsc_adapter,
    bom_warnings_adapter,
    news_feed,
)


class FakeCursor:
    def __init__(self):
        self._fetch = None
        self.last_id = 0

    def execute(self, query, params):
        q = query.strip()
        if q.startswith("SELECT id FROM sources"):
            self._fetch = (1,)
        elif q.startswith("INSERT INTO sources"):
            self._fetch = (1,)
        elif q.startswith("INSERT INTO events"):
            self.last_id += 1
            self._fetch = (self.last_id,)
        else:
            self._fetch = None

    def fetchone(self):
        return self._fetch

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def fake_get_conn():
    return FakeConn()


def load_fixture(name: str):
    path = pathlib.Path(__file__).resolve().parents[1] / "ingest" / "fixtures" / name
    with open(path, "r", encoding="utf-8") as f:
        if name.endswith(".xml"):
            return f.read()
        return json.load(f)


def _persist(events, meta):
    run.dbmod.get_conn = fake_get_conn
    return run.persist(events, *meta)


def test_ais_adapter_normalizes_and_persists():
    data = load_fixture("ais_sample.json")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = ais.normalize(raw)
    assert events
    count = _persist(events, ais.get_source_meta("http://example"))
    assert count == len(events)


def test_bushfire_adapter_normalizes_and_persists():
    data = load_fixture("bushfire_alerts_sample.json")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = bushfire_alerts.normalize(raw)
    assert events
    count = _persist(events, bushfire_alerts.get_source_meta("http://example"))
    assert count == len(events)


def test_cyber_adapter_normalizes_and_persists():
    data = load_fixture("cyber_advisories_sample.json")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = cyber_advisories.normalize(raw)
    assert events
    count = _persist(events, cyber_advisories.get_source_meta("http://example"))
    assert count == len(events)


def test_news_adapter_normalizes_and_persists():
    data = load_fixture("news_feed_sample.xml")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = news_feed.normalize(raw)
    assert events
    count = _persist(events, news_feed.get_source_meta("http://example"))
    assert count == len(events)


def test_acsc_adapter_normalizes_and_persists():
    data = load_fixture("acsc_alerts_sample.xml")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = acsc_adapter.normalize(raw)
    assert events
    count = _persist(events, acsc_adapter.get_source_meta("http://example"))
    assert count == len(events)


def test_bom_warnings_adapter_normalizes_and_persists():
    data = load_fixture("bom_warnings_sample.xml")
    raw = RawPayload(source_name="test", fetched_at=datetime.utcnow(), url="http://example", content=data)
    events = bom_warnings_adapter.normalize(raw)
    assert events
    # All events should be weather type
    assert all(ev.event_type == "weather" for ev in events)
    count = _persist(events, bom_warnings_adapter.get_source_meta("http://example"))
    assert count == len(events)
