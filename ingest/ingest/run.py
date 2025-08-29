import argparse
from datetime import datetime
from typing import List

from .common.schemas import NormalizedEvent
from .common import db as dbmod


def run_adapter(name: str) -> List[NormalizedEvent]:
    if name == "au_wildfire_fixture":
        from .adapters import au_wildfire_fixture as adapter
    else:
        raise SystemExit(f"Unknown adapter: {name}")

    raw = adapter.load_fixture()
    events = adapter.normalize(raw)
    return events


def persist(events: List[NormalizedEvent], source_name: str, source_url: str, source_type: str) -> int:
    count = 0
    with dbmod.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = dbmod.ensure_source(cur, source_name, source_url, source_type)
            for ev in events:
                dbmod.insert_event(
                    cur,
                    source_id=source_id,
                    title=ev.title,
                    body=ev.body,
                    event_type=ev.event_type,
                    occurred_at=ev.occurred_at.isoformat() if ev.occurred_at else None,
                    lat=ev.lat,
                    lon=ev.lon,
                    jurisdiction=ev.jurisdiction,
                    confidence=ev.confidence,
                    severity=ev.severity,
                )
                count += 1
        conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description="Run an ingestion adapter once")
    parser.add_argument("--adapter", default="au_wildfire_fixture", help="Adapter name")
    args = parser.parse_args()

    if args.adapter == "au_wildfire_fixture":
        from .adapters import au_wildfire_fixture as adapter
    else:
        raise SystemExit(f"Unknown adapter: {args.adapter}")

    raw = adapter.load_fixture()
    events = adapter.normalize(raw)
    source_name, source_url, source_type = adapter.get_source_meta()
    inserted = persist(events, source_name, source_url, source_type)
    print({
        "adapter": args.adapter,
        "fetched_at": datetime.utcnow().isoformat(),
        "events_normalized": len(events),
        "events_inserted": inserted,
    })


if __name__ == "__main__":
    main()

