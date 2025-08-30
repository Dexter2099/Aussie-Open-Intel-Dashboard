import pathlib
import sys

BASE_PATH = pathlib.Path(__file__).resolve()
sys.path.append(str(BASE_PATH.parents[2]))
sys.path.append(str(BASE_PATH.parents[1]))

from ingest import acsc_adapter, common  # type: ignore


def load_fixture(name: str) -> str:
    path = BASE_PATH.parents[1] / "ingest" / "fixtures" / name
    return path.read_text(encoding="utf-8")


class FakeCursor:
    def __init__(self):
        self.events = []
        self._fetch = None

    def execute(self, query, params=None):
        q = query.strip()
        if q.startswith("SELECT id FROM sources"):
            self._fetch = (1,)
        elif q.startswith("INSERT INTO sources"):
            self._fetch = (1,)
        elif q.startswith("SELECT 1 FROM events"):
            src, title, occurred = params
            for ev in self.events:
                if ev[0] == src and ev[1] == title and ev[4] == occurred:
                    self._fetch = (1,)
                    break
            else:
                self._fetch = None
        elif q.startswith("INSERT INTO events"):
            # params: source_id, title, body, event_type, occurred_at, jurisdiction, confidence, severity
            self.events.append(params)
            self._fetch = (len(self.events),)
        else:
            self._fetch = None

    def fetchone(self):
        return self._fetch

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_acsc_rss_insert_and_dedupe(monkeypatch):
    xml = load_fixture("acsc_alerts_sample.xml")
    events = acsc_adapter.parse(xml)
    assert events
    conn = FakeConn()
    monkeypatch.setattr(common, "get_conn", lambda: conn)
    count1 = acsc_adapter.insert_events(events)
    assert count1 >= 1
    count2 = acsc_adapter.insert_events(events)
    assert count2 == 0
    # ensure at least one inserted event has type 'cyber'
    assert any(ev[3] == "cyber" for ev in conn.cursor_obj.events)
