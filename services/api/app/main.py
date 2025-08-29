import logging
from uuid import uuid4

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from fastapi import FastAPI, Query, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, JSONResponse
from typing import Optional, List
from datetime import datetime

from .schemas import (
    Event,
    Entity,
    Notebook,
    NotebookCreate,
    NotebookUpdate,
    SearchQuery,
)
from .db import fetch_all, fetch_one
from .auth import get_current_user

logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

app = FastAPI(
    title="Aussie Open Intelligence API",
    default_response_class=ORJSONResponse,
    dependencies=[Depends(get_current_user)],
)

# Permissive CORS for early development; tighten later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    clear_contextvars()
    bind_contextvars(request_id=request_id, source="api")
    response = await call_next(request)
    logger.info(
        "request",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
    )
    return response


@app.exception_handler(Exception)
async def handle_exceptions(request: Request, exc: Exception):
    logger.error("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


@app.get("/search")
async def search(
    q: Optional[str] = None,
    bbox: Optional[str] = None,
    time_range: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "detected_at",
    source_id: Optional[int] = None,
    debug: int = 0,
):
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

    # Source filter
    if source_id:
        clauses.append("source_id = %s")
        params.append(int(source_id))

    clamped_limit = max(1, min(int(limit or 50), 500))
    clamped_offset = max(0, int(offset or 0))
    sort_col = "detected_at" if (sort not in {"detected_at", "occurred_at"}) else sort
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    geom_debug = ", CASE WHEN e.geom IS NOT NULL THEN ST_AsText(e.geom::geometry) END AS geom_wkt" if debug else ""
    sql = f"""
        SELECT e.id, e.source_id, s.name AS source_name, e.title, e.body, e.event_type, e.occurred_at, e.detected_at, e.jurisdiction, e.confidence, e.severity,
               CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
               CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat{geom_debug}
        FROM events e
        LEFT JOIN sources s ON s.id = e.source_id
        {where}
        ORDER BY {sort_col} DESC
        OFFSET %s
        LIMIT %s
    """
    params.extend([clamped_offset, clamped_limit])
    rows = fetch_all(sql, params)
    return {
        "query": {"q": q, "bbox": bbox, "time_range": time_range, "limit": clamped_limit, "offset": clamped_offset, "sort": sort_col},
        "results": rows,
    }


@app.get("/events/{event_id:int}")
async def get_event(event_id: int, debug_geom: int = 0):
    if debug_geom:
        row = fetch_one(
            """
            SELECT e.id, e.source_id, s.name AS source_name, e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
                   e.jurisdiction, e.confidence, e.severity,
                   CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
                   CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat,
                   CASE WHEN e.geom IS NOT NULL THEN ST_AsText(e.geom::geometry) END AS geom_wkt
            FROM events e
            LEFT JOIN sources s ON s.id = e.source_id
            WHERE e.id=%s
            """,
            (event_id,),
        )
    else:
        row = fetch_one(
            """
            SELECT e.id, e.source_id, s.name AS source_name, e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
                   e.jurisdiction, e.confidence, e.severity,
                   CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
                   CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat
            FROM events e
            LEFT JOIN sources s ON s.id = e.source_id
            WHERE e.id=%s
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
async def get_notebook(notebook_id: int, user: dict = Depends(get_current_user)):
    row = fetch_one(
        """
        SELECT id, owner, title, items, created_at
        FROM notebooks
        WHERE id=%s AND owner=%s
        """,
        (notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return row


@app.post("/notebooks", response_model=Notebook)
async def create_notebook(nb: NotebookCreate, user: dict = Depends(get_current_user)):
    row = fetch_one(
        """
        INSERT INTO notebooks (owner, title, items)
        VALUES (%s, %s, %s)
        RETURNING id, owner, title, items, created_at
        """,
        (user.get("sub"), nb.title, nb.items),
    )
    return row


@app.put("/notebooks/{notebook_id}", response_model=Notebook)
async def update_notebook(
    notebook_id: int, nb: NotebookUpdate, user: dict = Depends(get_current_user)
):
    row = fetch_one(
        """
        UPDATE notebooks
        SET title = COALESCE(%s, title), items = COALESCE(%s, items)
        WHERE id=%s AND owner=%s
        RETURNING id, owner, title, items, created_at
        """,
        (nb.title, nb.items, notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return row


@app.get("/notebooks/{notebook_id}/export")
async def export_notebook(
    notebook_id: int, fmt: str = Query("md", pattern="^(md|markdown|json|pdf)$"), user: dict = Depends(get_current_user)
):
    nb = fetch_one(
        """
        SELECT id, owner, title, items, created_at
        FROM notebooks
        WHERE id=%s AND owner=%s
        """,
        (notebook_id, user.get("sub")),
    )
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if fmt in {"json"}:
        return JSONResponse(nb)
    if fmt in {"md", "markdown"}:
        lines = [f"# {nb['title']}", ""]
        for item in nb.get("items", []):
            if isinstance(item, dict) and "event" in item:
                lines.append(f"- Event {item['event']}")
            else:
                lines.append(f"- {item}")
        return Response("\n".join(lines), media_type="text/markdown")
    if fmt == "pdf":
        from io import BytesIO
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf)
        y = 800
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, nb["title"])
        c.setFont("Helvetica", 12)
        y -= 40
        for item in nb.get("items", []):
            text = (
                f"- Event {item['event']}" if isinstance(item, dict) and "event" in item else f"- {item}"
            )
            c.drawString(40, y, text)
            y -= 20
        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()
        buf.close()
        return Response(content=pdf_bytes, media_type="application/pdf")
    raise HTTPException(status_code=400, detail="Unsupported format")


@app.get("/events/recent")
async def recent_events(limit: int = 50, offset: int = 0, sort: str = "detected_at", source_id: Optional[int] = None, debug: int = 0):
    clamped = max(1, min(int(limit or 50), 200))
    clamped_offset = max(0, int(offset or 0))
    sort_col = "detected_at" if (sort not in {"detected_at", "occurred_at"}) else sort
    clauses: List[str] = []
    params: List = []
    if source_id:
        clauses.append("e.source_id = %s")
        params.append(int(source_id))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    geom_debug = ", CASE WHEN e.geom IS NOT NULL THEN ST_AsText(e.geom::geometry) END AS geom_wkt" if debug else ""
    rows = fetch_all(
        f"""
        SELECT e.id, e.source_id, s.name AS source_name, e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
               e.jurisdiction, e.confidence, e.severity,
               CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
               CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat{geom_debug}
        FROM events e
        LEFT JOIN sources s ON s.id = e.source_id
        {where}
        ORDER BY {sort_col} DESC
        OFFSET %s
        LIMIT %s
        """,
        params + [clamped_offset, clamped],
    )
    return {"results": rows, "limit": clamped, "offset": clamped_offset, "sort": sort_col}


@app.get("/stats/summary")
async def stats_summary(q: Optional[str] = None, bbox: Optional[str] = None, time_range: Optional[str] = None, source_id: Optional[int] = None):
    params: List = []
    clauses: List[str] = []

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
            clauses.append("geom IS NOT NULL AND ST_Intersects(geom, geography(ST_MakeEnvelope(%s,%s,%s,%s,4326)))")
            params.extend([minlon, minlat, maxlon, maxlat])
        except Exception:
            pass

    if source_id:
        clauses.append("source_id = %s")
        params.append(int(source_id))

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    total = fetch_all(f"SELECT count(*) AS c FROM events {where}", params)[0]["c"] if True else 0
    by_type = fetch_all(f"SELECT event_type, count(*) AS c FROM events {where} GROUP BY event_type ORDER BY c DESC", params)
    by_source = fetch_all(f"SELECT s.name AS source_name, count(*) AS c FROM events e LEFT JOIN sources s ON s.id=e.source_id {where.replace(' WHERE ',' WHERE ')} GROUP BY s.name ORDER BY c DESC", params)
    return {"total": total, "counts_by_type": by_type, "counts_by_source": by_source}


@app.get("/events/geojson")
async def events_geojson(q: Optional[str] = None, bbox: Optional[str] = None, time_range: Optional[str] = None, limit: int = 500, source_id: Optional[int] = None):
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

    if source_id:
        clauses.append("e.source_id = %s")
        params.append(int(source_id))

    clamped = max(1, min(int(limit or 500), 1000))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = fetch_all(
        f"""
        SELECT e.id, e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
               ST_X(e.geom::geometry) AS lon, ST_Y(e.geom::geometry) AS lat,
               e.jurisdiction, e.confidence, e.severity,
               s.name AS source_name
        FROM events e
        LEFT JOIN sources s ON s.id = e.source_id
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


@app.get("/sources")
async def list_sources():
    rows = fetch_all(
        """
        SELECT id, name, type
        FROM sources
        ORDER BY name ASC
        """
    )
    return {"results": rows, "count": len(rows)}
