from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any
from datetime import datetime


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
    geom: Optional[Any] = Field(default=None, description="Point/Polygon geometry placeholder")
    raw: Optional[Any] = None


class Entity(BaseModel):
    id: int
    type: Literal["Person", "Org", "Vessel", "Aircraft", "Location", "Asset", "EventType"]
    name: str
    canonical_key: Optional[str] = None
    attrs: dict = {}


class Notebook(BaseModel):
    id: int
    owner: str
    title: str
    items: list
    created_at: Optional[datetime] = None


class NotebookCreate(BaseModel):
    title: str
    items: list


class NotebookUpdate(BaseModel):
    title: Optional[str] = None
    items: Optional[list] = None


class SearchQuery(BaseModel):
    q: Optional[str] = None
    bbox: Optional[str] = None
    time_range: Optional[str] = None
    limit: int = 50

