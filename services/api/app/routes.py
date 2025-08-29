from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from .auth import get_current_user
from .db import fetch_all, fetch_one


router = APIRouter(prefix="/v1", dependencies=[Depends(get_current_user)])


def _parse_timerange(rng: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
    if not rng:
        return None, None
    try:
        start_s, end_s = rng.split("..", 1)
    except ValueError:
        start_s, end_s = rng, ""

    def _p(ts: Optional[str]) -> Optional[datetime]:
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

    return _p(start_s), _p(end_s)


@router.get("/search")
async def search(
    q: Optional[str] = Query(default=None, description="Full-text query on title/body"),
    bbox: Optional[str] = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    time_range: Optional[str] = Query(default=None, description="ISO8601 start..end on occurred_at"),
    source_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
):
    clauses: List[str] = []
    params: List = []

    # FTS on title/body using expression index
    if q:
        clauses.append(
            "to_tsvector('simple', e.title || ' ' || coalesce(e.body,'')) @@ plainto_tsquery('simple', %s)"
        )
        params.append(q)

    # Time window on occurred_at
    start_dt, end_dt = _parse_timerange(time_range)
    if start_dt:
        clauses.append("e.occurred_at >= %s")
        params.append(start_dt)
    if end_dt:
        clauses.append("e.occurred_at <= %s")
        params.append(end_dt)

    # Optional bbox on geom (geography) if provided
    if bbox:
        try:
            minlon, minlat, maxlon, maxlat = [float(x) for x in bbox.split(",")]
            clauses.append(
                "e.geom IS NOT NULL AND ST_Intersects(e.geom, geography(ST_MakeEnvelope(%s,%s,%s,%s,4326)))"
            )
            params.extend([minlon, minlat, maxlon, maxlat])
        except Exception:
            # ignore malformed bbox
            pass

    if source_id:
        clauses.append("e.source_id = %s")
        params.append(int(source_id))

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    rows = fetch_all(
        f"""
        SELECT e.id, e.source_id, s.name AS source_name, s.url AS source_url,
               e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
               e.jurisdiction, e.confidence, e.severity,
               CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
               CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat
        FROM events e
        LEFT JOIN sources s ON s.id = e.source_id
        {where}
        ORDER BY e.detected_at DESC
        LIMIT %s
        """,
        params + [int(limit)],
    )

    features = []
    for r in rows:
        lon = r.pop("lon", None)
        lat = r.pop("lat", None)
        geom = None
        if lon is not None and lat is not None:
            geom = {"type": "Point", "coordinates": [lon, lat]}

        # Expose a 'raw_ref' derived from source URL if present
        raw_ref = r.get("source_url")
        props = dict(r)
        props["raw_ref"] = raw_ref
        features.append({"type": "Feature", "id": r["id"], "geometry": geom, "properties": props})

    return {"type": "FeatureCollection", "features": features}


@router.get("/events/{event_id}")
async def get_event(event_id: int):
    ev = fetch_one(
        """
        SELECT e.id, e.source_id, s.name AS source_name, s.url AS source_url,
               e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
               e.jurisdiction, e.confidence, e.severity,
               CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
               CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat
        FROM events e
        LEFT JOIN sources s ON s.id = e.source_id
        WHERE e.id=%s
        """,
        (event_id,),
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    entities = fetch_all(
        """
        SELECT ee.entity_id AS id, ee.relation, ee.score,
               en.type, en.name, en.attrs
        FROM event_entities ee
        JOIN entities en ON en.id = ee.entity_id
        WHERE ee.event_id=%s
        ORDER BY coalesce(ee.score, 0) DESC, en.name ASC
        """,
        (event_id,),
    )

    lon = ev.pop("lon", None)
    lat = ev.pop("lat", None)
    geometry = None
    if lon is not None and lat is not None:
        geometry = {"type": "Point", "coordinates": [lon, lat]}

    detail = {
        "id": ev["id"],
        "geometry": geometry,
        "properties": ev,
        "raw_ref": ev.get("source_url"),
        "entities": entities,
    }
    return detail


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: int):
    # Stub: Return minimal shape for now
    row = fetch_one(
        "SELECT id, type, name, canonical_key, attrs FROM entities WHERE id=%s",
        (entity_id,),
    )
    if not row:
        # basic stub
        return {"id": entity_id, "type": "Org", "name": "Unknown", "attrs": {}}
    return row

