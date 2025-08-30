import logging
from uuid import UUID, uuid4

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from fastapi import FastAPI, Query, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import base64
import os

from .schemas import (
    Event,
    Entity,
    Notebook,
    NotebookCreate,
    NotebookUpdate,
    SearchQuery,
)
from .db import fetch_all, fetch_one, get_conn
from .auth import get_current_user, create_access_token
from .routes import router as v1_router
from .config import get_settings
import redis
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

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

# Mount v1 API routes
app.include_router(v1_router)

REQUEST_COUNTER = Counter("request_total", "Total HTTP requests")
ERROR_COUNTER = Counter("error_total", "Total HTTP errors")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/token", response_model=Token, include_in_schema=True)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Issue a JWT for the supplied credentials.

    This is a stub implementation that accepts any username and password and
    returns a signed JWT identifying the user by ``sub``.
    """

    user = {"sub": form_data.username}
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    REQUEST_COUNTER.inc()
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            ERROR_COUNTER.inc()
        return response
    except Exception:
        ERROR_COUNTER.inc()
        raise


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


@app.get("/healthz")
async def healthz():
    settings = get_settings()
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        redis.Redis(host=settings.redis_host, port=settings.redis_port).ping()
    except Exception:
        raise HTTPException(status_code=500, detail="unhealthy")
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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


@app.get("/events", response_model=List[Event], response_model_exclude_none=True)
async def list_events(
    response: Response,
    type: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    bbox: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    include_raw: int = 0,
):
    """Return a slice of events filtered by the supplied query params.

    The results are ordered by ``detected_at`` and ``id`` descending to allow
    stable cursor based pagination.  A ``cursor`` for the next page is returned
    in the ``X-Next-Cursor`` header when another page of results is available.

    The SQL query uses indexed columns (``event_type`` and ``detected_at``) and
    optionally PostGIS spatial indexes when available.
    """

    clauses: List[str] = []
    params: List = []

    if type:
        clauses.append("e.event_type = %s")
        params.append(type)
    if since:
        clauses.append("e.detected_at >= %s")
        params.append(since)
    if until:
        clauses.append("e.detected_at <= %s")
        params.append(until)
    if q:
        clauses.append("e.title ILIKE %s")
        params.append(f"%{q}%")
    if bbox:
        try:
            minlon, minlat, maxlon, maxlat = [float(x) for x in bbox.split(",")]
            if os.getenv("USE_POSTGIS", "1") == "1":
                clauses.append(
                    "e.geom IS NOT NULL AND ST_Intersects(e.geom, geography(ST_MakeEnvelope(%s,%s,%s,%s,4326)))"
                )
            else:
                clauses.append(
                    "e.geom IS NOT NULL AND ST_X(e.geom::geometry) BETWEEN %s AND %s AND ST_Y(e.geom::geometry) BETWEEN %s AND %s"
                )
            params.extend([minlon, minlat, maxlon, maxlat])
        except Exception:
            pass
    if cursor:
        try:
            dec = base64.urlsafe_b64decode(cursor.encode()).decode()
            ts_s, id_s = dec.split("|", 1)
            cur_ts = datetime.fromisoformat(ts_s)
            cur_id = int(id_s)
            clauses.append("(e.detected_at, e.id) < (%s, %s)")
            params.extend([cur_ts, cur_id])
        except Exception:
            pass

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    raw_col = ", e.raw" if include_raw else ""
    sql = f"""
        SELECT e.id, e.source_id, e.title, e.body, e.event_type, e.occurred_at, e.detected_at,
               e.jurisdiction, e.confidence, e.severity,
               CASE WHEN e.geom IS NOT NULL THEN ST_X(e.geom::geometry) END AS lon,
               CASE WHEN e.geom IS NOT NULL THEN ST_Y(e.geom::geometry) END AS lat{raw_col}
        FROM events e
        {where}
        ORDER BY e.detected_at DESC, e.id DESC
        LIMIT %s
    """
    params.append(limit)
    rows = fetch_all(sql, params)
    events = []
    for r in rows:
        lon = r.pop("lon", None)
        lat = r.pop("lat", None)
        geom = None
        if lon is not None and lat is not None:
            geom = {"type": "Point", "coordinates": [lon, lat]}
        raw = r.pop("raw", None)
        evt = dict(r)
        evt["geom"] = geom
        if include_raw:
            evt["raw"] = raw
        events.append(evt)
    if len(rows) == limit:
        last = rows[-1]
        next_cursor = base64.urlsafe_b64encode(
            f"{last['detected_at'].isoformat()}|{last['id']}".encode()
        ).decode()
        if response is not None:
            response.headers["X-Next-Cursor"] = next_cursor
    return events


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


@app.get("/events/{event_id:uuid}")
async def get_event_detail(event_id: UUID, include_raw: int = 0):
    row = fetch_one(
        """
        SELECT id, type, title, time,
               CASE WHEN location IS NOT NULL THEN ST_X(location::geometry) END AS lon,
               CASE WHEN location IS NOT NULL THEN ST_Y(location::geometry) END AS lat,
               source, raw
        FROM events
        WHERE id=%s
        """,
        (event_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    entities = fetch_all(
        """
        SELECT e.id, e.type AS kind, e.name AS label
        FROM event_entities ee
        JOIN entities e ON e.id = ee.entity_id
        WHERE ee.event_id=%s
        """,
        (event_id,),
    )
    lon = row.pop("lon", None)
    lat = row.pop("lat", None)
    location = None
    if lon is not None and lat is not None:
        location = {"type": "Point", "coordinates": [lon, lat]}
    raw = row.pop("raw", None)
    event = dict(row)
    event["location"] = location
    event["entities"] = entities
    if include_raw:
        event["raw"] = raw
    return event


@app.get("/entities/{entity_id:uuid}")
async def get_entity(entity_id: UUID):
    ent = fetch_one(
        """SELECT id, type AS kind, name AS label FROM entities WHERE id=%s""",
        (entity_id,),
    )
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    events = fetch_all(
        """
        SELECT e.id, e.type, e.title, e.time
        FROM event_entities ee
        JOIN events e ON e.id = ee.event_id
        WHERE ee.entity_id=%s
        ORDER BY e.time DESC
        LIMIT 20
        """,
        (entity_id,),
    )
    ent["events"] = events
    return ent


@app.get("/graph")
async def graph(
    entity_id: int = Query(..., description="Root entity id"),
    max: int = Query(200, ge=1, le=1000),
):
    """Return a simple two-hop graph neighbourhood.

    Nodes represent events or entities. Edges connect entities to events and
    co-occurring entities. Results are capped by ``max``.
    """

    # First, find events linked to the root entity
    ev_rows = fetch_all(
        """
        SELECT event_id
        FROM event_entities
        WHERE entity_id=%s
        ORDER BY event_id
        LIMIT %s
        """,
        (entity_id, max),
    )
    event_ids = [r["event_id"] for r in ev_rows]
    if not event_ids:
        return {"nodes": [], "edges": []}

    # All entity-event edges within these events
    ee_rows = fetch_all(
        """
        SELECT event_id, entity_id
        FROM event_entities
        WHERE event_id = ANY(%s)
        LIMIT %s
        """,
        (event_ids, max),
    )
    entity_ids = sorted({row["entity_id"] for row in ee_rows})

    # Entity details
    ent_rows = fetch_all(
        "SELECT id, type, name FROM entities WHERE id = ANY(%s)",
        (entity_ids,),
    )
    ent_lookup = {r["id"]: r for r in ent_rows}

    # Event details
    evt_rows = fetch_all(
        "SELECT id, event_type, title FROM events WHERE id = ANY(%s)",
        (event_ids,),
    )
    evt_lookup = {r["id"]: r for r in evt_rows}

    nodes = []
    for eid in entity_ids:
        ent = ent_lookup.get(eid, {})
        nodes.append(
            {
                "id": eid,
                "label": ent.get("name"),
                "kind": "entity",
                "type": ent.get("type"),
            }
        )
    for eid in event_ids:
        ev = evt_lookup.get(eid, {})
        nodes.append(
            {
                "id": eid,
                "label": ev.get("title"),
                "kind": "event",
                "type": ev.get("event_type"),
            }
        )

    edges = []
    for r in ee_rows:
        edges.append({"source": r["entity_id"], "target": r["event_id"], "weight": 1})

    # Entity co-occurrence edges
    pair_rows = fetch_all(
        """
        SELECT ee1.entity_id AS src, ee2.entity_id AS dst, COUNT(*) AS weight
        FROM event_entities ee1
        JOIN event_entities ee2 ON ee1.event_id = ee2.event_id
        WHERE ee1.entity_id < ee2.entity_id AND ee1.event_id = ANY(%s)
        GROUP BY src, dst
        LIMIT %s
        """,
        (event_ids, max),
    )
    for r in pair_rows:
        edges.append({"source": r["src"], "target": r["dst"], "weight": r["weight"]})

    return {"nodes": nodes, "edges": edges}


@app.get("/graph/entity/{entity_id}")
async def graph_entity(entity_id: int):
    ent = fetch_one("SELECT id, type, name FROM entities WHERE id=%s", (entity_id,))
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    rel_rows = fetch_all(
        """
        SELECT r.src_entity, r.dst_entity, r.relation,
               s.type AS src_type, s.name AS src_name,
               d.type AS dst_type, d.name AS dst_name
        FROM relations r
        JOIN entities s ON s.id = r.src_entity
        JOIN entities d ON d.id = r.dst_entity
        WHERE r.src_entity=%s OR r.dst_entity=%s
        """,
        (entity_id, entity_id),
    )
    nodes = {ent["id"]: {"id": ent["id"], "label": f"{ent['type']}: {ent['name']}"}}
    edges = []
    for r in rel_rows:
        for eid, etype, name in [
            (r["src_entity"], r["src_type"], r["src_name"]),
            (r["dst_entity"], r["dst_type"], r["dst_name"]),
        ]:
            if eid not in nodes:
                nodes[eid] = {"id": eid, "label": f"{etype}: {name}"}
        edges.append({"src": r["src_entity"], "dst": r["dst_entity"], "relation": r["relation"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@app.get("/graph/event/{event_id}")
async def graph_event(event_id: int):
    ev = fetch_one("SELECT id, title FROM events WHERE id=%s", (event_id,))
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    rows = fetch_all(
        """
        SELECT ee.entity_id, ee.relation, e.type, e.name
        FROM event_entities ee
        JOIN entities e ON e.id = ee.entity_id
        WHERE ee.event_id=%s
        """,
        (event_id,),
    )
    nodes = {event_id: {"id": event_id, "label": f"Event: {ev['title']}"}}
    edges = []
    for r in rows:
        eid = r["entity_id"]
        if eid not in nodes:
            nodes[eid] = {"id": eid, "label": f"{r['type']}: {r['name']}"}
        edges.append({"src": event_id, "dst": eid, "relation": r["relation"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@app.get("/notebooks", response_model=list[Notebook])
async def list_notebooks(user: dict = Depends(get_current_user)):
    rows = fetch_all(
        """
        SELECT id, created_by, title, created_at
        FROM notebooks
        WHERE created_by=%s
        ORDER BY created_at DESC
        """,
        (user.get("sub"),),
    )
    return rows


@app.get("/notebooks/{notebook_id}", response_model=Notebook)
async def get_notebook(notebook_id: UUID, user: dict = Depends(get_current_user)):
    nb = fetch_one(
        """
        SELECT id, created_by, title, created_at
        FROM notebooks
        WHERE id=%s AND created_by=%s
        """,
        (notebook_id, user.get("sub")),
    )
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    items = fetch_all(
        """
        SELECT id, notebook_id, kind, ref_id, note, created_at
        FROM notebook_items
        WHERE notebook_id=%s
        ORDER BY created_at ASC
        """,
        (notebook_id,),
    )
    nb["items"] = items
    return nb


@app.post("/notebooks", response_model=Notebook)
async def create_notebook(nb: NotebookCreate, user: dict = Depends(get_current_user)):
    new_id = uuid4()
    row = fetch_one(
        """
        INSERT INTO notebooks (id, created_by, title)
        VALUES (%s, %s, %s)
        RETURNING id, created_by, title, created_at
        """,
        (new_id, user.get("sub"), nb.title),
    )
    return row


@app.put("/notebooks/{notebook_id}", response_model=Notebook)
async def update_notebook(
    notebook_id: UUID, nb: NotebookUpdate, user: dict = Depends(get_current_user)
):
    row = fetch_one(
        """
        UPDATE notebooks
        SET title = COALESCE(%s, title)
        WHERE id=%s AND created_by=%s
        RETURNING id, created_by, title, created_at
        """,
        (nb.title, notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return row


@app.delete("/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: UUID, user: dict = Depends(get_current_user)):
    row = fetch_one(
        """
        DELETE FROM notebooks WHERE id=%s AND created_by=%s RETURNING id
        """,
        (notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"status": "deleted", "id": str(notebook_id)}


@app.post("/notebooks/{notebook_id}/items")
async def add_notebook_item(
    notebook_id: UUID,
    item: dict,
    user: dict = Depends(get_current_user),
):
    # Expecting: {kind: 'event'|'entity', ref_id: UUID, note?: str}
    kind = (item.get("kind") or "").lower()
    if kind not in {"event", "entity"}:
        raise HTTPException(status_code=400, detail="Invalid kind")
    ref_id = item.get("ref_id")
    if not ref_id:
        raise HTTPException(status_code=400, detail="Missing ref_id")
    note = item.get("note")
    new_id = uuid4()
    row = fetch_one(
        """
        INSERT INTO notebook_items (id, notebook_id, kind, ref_id, note)
        SELECT %s, %s, %s, %s, %s
        WHERE EXISTS (SELECT 1 FROM notebooks WHERE id=%s AND created_by=%s)
        RETURNING id, notebook_id, kind, ref_id, note, created_at
        """,
        (new_id, notebook_id, kind, ref_id, note, notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return row


@app.delete("/notebooks/{notebook_id}/items")
async def delete_notebook_item(
    notebook_id: UUID,
    payload: dict,
    user: dict = Depends(get_current_user),
):
    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Missing item_id")
    row = fetch_one(
        """
        DELETE FROM notebook_items WHERE id=%s AND notebook_id=%s AND EXISTS (
            SELECT 1 FROM notebooks WHERE id=%s AND created_by=%s
        ) RETURNING id
        """,
        (item_id, notebook_id, notebook_id, user.get("sub")),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted", "id": item_id}


@app.get("/notebooks/{notebook_id}/export")
async def export_notebook(
    notebook_id: UUID, fmt: str = Query("md", pattern="^(md|markdown|json|pdf)$"), user: dict = Depends(get_current_user)
):
    nb = fetch_one(
        """
        SELECT id, created_by, title, created_at
        FROM notebooks
        WHERE id=%s AND created_by=%s
        """,
        (notebook_id, user.get("sub")),
    )
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    items = fetch_all(
        """
        SELECT id, kind, ref_id, note, created_at
        FROM notebook_items
        WHERE notebook_id=%s
        ORDER BY created_at ASC
        """,
        (notebook_id,),
    )

    # Build a rich representation with sources and timestamps
    enriched: list[dict] = []
    for it in items:
        if it.get("kind") == "event":
            ev = fetch_one(
                """
                SELECT e.id, e.title, e.time, s.url AS source_url
                FROM events e LEFT JOIN sources s ON s.id = e.source_id
                WHERE e.id=%s
                """,
                (it.get("ref_id"),),
            ) or {}
            enriched.append(
                {
                    "kind": "event",
                    "id": str(ev.get("id") or it.get("ref_id")),
                    "title": ev.get("title"),
                    "time": (ev.get("time").isoformat() if isinstance(ev.get("time"), datetime) else ev.get("time")),
                    "source_url": ev.get("source_url"),
                    "note": it.get("note"),
                    "created_at": (it.get("created_at").isoformat() if isinstance(it.get("created_at"), datetime) else it.get("created_at")),
                }
            )
        elif it.get("kind") == "entity":
            en = fetch_one(
                """SELECT id, type, name FROM entities WHERE id=%s""",
                (it.get("ref_id"),),
            ) or {}
            enriched.append(
                {
                    "kind": "entity",
                    "id": str(en.get("id") or it.get("ref_id")),
                    "type": en.get("type"),
                    "name": en.get("name"),
                    "note": it.get("note"),
                    "created_at": (it.get("created_at").isoformat() if isinstance(it.get("created_at"), datetime) else it.get("created_at")),
                }
            )
        else:
            enriched.append({"kind": it.get("kind"), "ref_id": str(it.get("ref_id")), "note": it.get("note")})

    if fmt in {"json"}:
        payload = {
            "id": str(nb["id"]),
            "title": nb["title"],
            "created_by": nb["created_by"],
            "created_at": (nb["created_at"].isoformat() if isinstance(nb.get("created_at"), datetime) else nb.get("created_at")),
            "items": enriched,
        }
        return JSONResponse(payload)
    if fmt in {"md", "markdown"}:
        lines = [f"# {nb['title']}", "", f"Created by: {nb['created_by']}", f"Created at: {(nb['created_at'].isoformat() if isinstance(nb.get('created_at'), datetime) else nb.get('created_at'))}", ""]
        for it in enriched:
            if it.get("kind") == "event":
                when = it.get("time") or ""
                src = it.get("source_url") or ""
                note = f" — {it['note']}" if it.get("note") else ""
                lines.append(f"- [Event] {it.get('title') or it.get('id')} ({when}) {src}{note}")
            elif it.get("kind") == "entity":
                note = f" — {it['note']}" if it.get("note") else ""
                lines.append(f"- [Entity] {it.get('type')}: {it.get('name') or it.get('id')}{note}")
            else:
                lines.append(f"- {it}")
        # Ensure a trailing blank line
        lines.append("")
        return Response("\n".join(lines) + "\n", media_type="text/markdown")
    if fmt == "pdf":
        from io import BytesIO
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf)
        y = 800
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, f"Notebook: {nb['title']}")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Created by: {nb['created_by']}")
        y -= 15
        c.drawString(40, y, f"Created at: {(nb['created_at'].isoformat() if isinstance(nb.get('created_at'), datetime) else nb.get('created_at'))}")
        y -= 30
        c.setFont("Helvetica", 12)
        for it in enriched:
            if y < 60:
                c.showPage()
                y = 800
                c.setFont("Helvetica", 12)
            if it.get("kind") == "event":
                text = f"- [Event] {it.get('title') or it.get('id')} ({it.get('time') or ''}) {it.get('source_url') or ''}"
            elif it.get("kind") == "entity":
                text = f"- [Entity] {it.get('type')}: {it.get('name') or it.get('id')}"
            else:
                text = f"- {it}"
            if it.get("note"):
                text += f" — {it.get('note')}"
            c.drawString(40, y, text)
            y -= 18
        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()
        if not pdf_bytes:
            pdf_bytes = b"%PDF-1.4\n%%EOF\n"
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
        SELECT id, name, url, type, legal_notes
        FROM sources
        ORDER BY name ASC
        """
    )
    return {"results": rows, "count": len(rows)}
