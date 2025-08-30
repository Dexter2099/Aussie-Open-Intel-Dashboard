from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Source(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    type: Optional[str] = None
    legal_notes: Optional[str] = None


EventType = Literal[
    "Weather",
    "Disaster",
    "Wildfire",
    "Earthquake",
    "Maritime",
    "Aviation",
    "GovLE",
    "Cyber",
    "Other",
]


class Event(BaseModel):
    id: int
    source_id: Optional[int] = None
    title: str
    body: Optional[str] = None
    event_type: EventType = "Other"
    occurred_at: Optional[datetime] = None
    detected_at: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[float] = None
    geom: Optional[dict] = Field(default=None, description="Point/Polygon geometry placeholder")
    raw: Optional[dict] = None


class Entity(BaseModel):
    id: int
    type: Literal["Person", "Org", "Vessel", "Aircraft", "Location", "Asset", "EventType"]
    name: str
    canonical_key: Optional[str] = None
    attrs: dict = {}


class NotebookItem(BaseModel):
    id: UUID
    kind: Literal['event', 'entity']
    ref_id: UUID
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    event: Optional[dict] = None
    entity: Optional[dict] = None


class Notebook(BaseModel):
    id: UUID
    title: str
    created_by: str
    created_at: Optional[datetime] = None
    items: List[NotebookItem] = []


class NotebookCreate(BaseModel):
    title: str


class NotebookUpdate(BaseModel):
    title: Optional[str] = None


class NotebookItemCreate(BaseModel):
    kind: Literal['event', 'entity']
    ref_id: UUID
    note: Optional[str] = None


class SearchQuery(BaseModel):
    q: Optional[str] = None
    bbox: Optional[str] = None
    time_range: Optional[str] = None
    limit: int = 50
