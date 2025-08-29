from datetime import datetime
from typing import List, Tuple

from ..common.schemas import RawPayload, NormalizedEvent


SOURCE_NAME = "AU Wildfire Fixture"


def load_fixture() -> RawPayload:
    import json, pathlib

    fixture_path = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "qld_wildfire_sample.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    return RawPayload(source_name=SOURCE_NAME, fetched_at=datetime.utcnow(), url=str(fixture_path), content=content)


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    items = raw.content.get("incidents", [])
    events: List[NormalizedEvent] = []
    for it in items:
        title = it.get("title") or it.get("name") or "Wildfire Incident"
        body = it.get("description") or it.get("summary")
        occurred = it.get("occurred_at")
        occurred_dt = None
        if occurred:
            try:
                occurred_dt = datetime.fromisoformat(occurred)
            except Exception:
                occurred_dt = None
        lat = it.get("lat")
        lon = it.get("lon")
        severity = None
        sev = it.get("severity")
        if isinstance(sev, (int, float)):
            severity = float(sev)
        jurisdiction = it.get("state") or it.get("jurisdiction") or "QLD"

        events.append(
            NormalizedEvent(
                title=title,
                body=body,
                event_type="Wildfire",
                occurred_at=occurred_dt,
                jurisdiction=jurisdiction,
                confidence=0.8,
                severity=severity,
                lat=lat,
                lon=lon,
                attrs={k: v for k, v in it.items() if k not in {"title", "name", "description", "summary", "occurred_at", "lat", "lon", "severity", "state", "jurisdiction"}},
            )
        )
    return events


def get_source_meta() -> Tuple[str, str, str]:
    # name, url, type
    return SOURCE_NAME, "fixture://qld_wildfire_sample.json", "Wildfire"

