from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class RawPayload(BaseModel):
    source_name: str
    fetched_at: datetime
    url: Optional[str] = None
    content: Any


class NormalizedEvent(BaseModel):
    title: str
    body: Optional[str] = None
    event_type: str = "Other"
    occurred_at: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[float] = None
    lat: Optional[float] = Field(default=None, description="Latitude, WGS84")
    lon: Optional[float] = Field(default=None, description="Longitude, WGS84")
    attrs: Dict[str, Any] = {}

