from datetime import datetime

from pydantic import BaseModel


class ActivityLog(BaseModel):
    id: str
    event_type: str
    event_subtype: str | None = None
    title: str
    message: str | None = None
    metadata: dict = {}
    created_at: datetime
