from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from typing import Optional, List
from datetime import datetime

from .schemas import Event, Entity, Notebook, SearchQuery
from .db import fetch_all, fetch_one

app = FastAPI(title="Aussie Open Intelligence API", default_response_class=ORJSONResponse)

# Permissive CORS for early development; tighten later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


@app.get("/search")
async def search(q: Optional[str] = None, bbox: Optional[str] = None, time_range: Optional[str] = None, limit: int = 50):
    params: List = []
    clauses: List[str] = []

    # Text filter
    if q:
        clauses.append("(title ILIKE %s OR body ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    # Time range filter: "start..end" (ISO8601); each side optional
    if time_range:
        try:
            start_s, end_s = time_range.split("..", 1)
        except ValueError:
            start_s, end_s = time_range, ""
        def _parse(ts: str | None):
            if not ts:
                return None
            ts = ts.strip()
            if not ts:
                return None
            # Accept Z suffix
            if ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return None
        start_dt = _parse(start_s)
        end_dt = _parse(end_s)
        if start_dt:
            clauses.append("detected_at >= %s")
            params.append(start_dt)
        if end_dt:
            clauses.append("detected_at <= %s")
            params.append(end_dt)

    # BBOX filter: "minLon,minLat,maxLon,maxLat"
    if bbox:
        try:
            minlon, minlat, maxlon, maxlat = [float(x) for x in bbox.split(",")]
            clauses.append("geom IS NOT NULL AND ST_Intersects(geom, geography(ST_MakeEnvelope(%s,%s,%s,%s,4326)))")
            params.extend([minlon, minlat, maxlon, maxlat])
        except Exception:
            pass

    clamped_limit = max(1, min(int(limit or 50), 500))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT id, source_id, title, body, event_type, occurred_at, detected_at, jurisdiction, confidence, severity,
               CASE WHEN geom IS NOT NULL THEN ST_X(geom::geometry) END AS lon,
               CASE WHEN geom IS NOT NULL THEN ST_Y(geom::geometry) END AS lat
        FROM events
        {where}
        ORDER BY detected_at DESC
        LIMIT %s
    """
    params.append(clamped_limit)
    rows = fetch_all(sql, params)
    return {
        "query": {"q": q, "bbox": bbox, "time_range": time_range, "limit": clamped_limit},
        "results": rows,
    }


@app.get("/events/{event_id}")
async def get_event(event_id: int):
    row = fetch_one(
        """
        SELECT id, source_id, title, body, event_type, occurred_at, detected_at, jurisdiction, confidence, severity
        FROM events WHERE id=%s
        """,
        (event_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return row


@app.get("/entities/{entity_id}", response_model=Entity)
async def get_entity(entity_id: int):
    return {"id": entity_id, "type": "Org", "name": "Placeholder Org", "attrs": {}}


@app.get("/graph")
async def graph(seed: Optional[int] = Query(default=None, description="Seed entity id")):
    return {
        "seed": seed,
        "nodes": [
            {"id": 1, "label": "Org: Example"},
            {"id": 2, "label": "Event: Sample"},
        ],
        "edges": [
            {"src": 1, "dst": 2, "relation": "INVOLVES"}
        ],
        "note": "Placeholder graph; back by relations table later",
    }


@app.get("/notebooks/{notebook_id}", response_model=Notebook)
async def get_notebook(notebook_id: int):
    return Notebook(id=notebook_id, owner="demo", title="Demo Notebook", items=[{"event": 1}])


@app.post("/notebooks", response_model=Notebook)
async def create_notebook(nb: Notebook):
    # Placeholder echo endpoint
    return nb


@app.get("/events/recent")
async def recent_events(limit: int = 50):
    clamped = max(1, min(int(limit or 50), 200))
    rows = fetch_all(
        """
        SELECT id, source_id, title, body, event_type, occurred_at, detected_at, jurisdiction, confidence, severity,
               CASE WHEN geom IS NOT NULL THEN ST_X(geom::geometry) END AS lon,
               CASE WHEN geom IS NOT NULL THEN ST_Y(geom::geometry) END AS lat
        FROM events
        ORDER BY detected_at DESC
        LIMIT %s
        """,
        (clamped,),
    )
    return {"results": rows, "limit": clamped}


@app.get("/events/geojson")
async def events_geojson(q: Optional[str] = None, bbox: Optional[str] = None, time_range: Optional[str] = None, limit: int = 500):
    params: List = []
    clauses: List[str] = ["geom IS NOT NULL"]

    if q:
        clauses.append("(title ILIKE %s OR body ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    if time_range:
        try:
            start_s, end_s = time_range.split("..", 1)
        except ValueError:
            start_s, end_s = time_range, ""
        def _parse(ts: str | None):
            if not ts:
                return None
            ts = ts.strip()
            if not ts:
                return None
            if ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return None
        start_dt = _parse(start_s)
        end_dt = _parse(end_s)
        if start_dt:
            clauses.append("detected_at >= %s")
            params.append(start_dt)
        if end_dt:
            clauses.append("detected_at <= %s")
            params.append(end_dt)

    if bbox:
        try:
            minlon, minlat, maxlon, maxlat = [float(x) for x in bbox.split(",")]
            clauses.append("ST_Intersects(geom, geography(ST_MakeEnvelope(%s,%s,%s,%s,4326)))")
            params.extend([minlon, minlat, maxlon, maxlat])
        except Exception:
            pass

    clamped = max(1, min(int(limit or 500), 1000))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = fetch_all(
        f"""
        SELECT id, title, body, event_type, occurred_at, detected_at,
               ST_X(geom::geometry) AS lon, ST_Y(geom::geometry) AS lat,
               jurisdiction, confidence, severity
        FROM events
        {where}
        ORDER BY detected_at DESC
        LIMIT %s
        """,
        params + [clamped],
    )

    features = []
    for r in rows:
        lon = r.pop("lon", None)
        lat = r.pop("lat", None)
        if lon is None or lat is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": r,
            }
        )

    return {"type": "FeatureCollection", "features": features, "count": len(features)}
