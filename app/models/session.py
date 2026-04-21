from datetime import date, datetime, timezone

from pydantic import BaseModel, Field

from app.models.triage import Intent


class GuestSession(BaseModel):
    guest_wa_id: str
    guest_name: str = "Guest"
    property_id: str | None = None
    detected_language: str = "en"
    message_count: int = 0
    last_intent: Intent | None = None
    checkout_date: date | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
