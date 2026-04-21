from enum import Enum

from pydantic import BaseModel


class Intent(str, Enum):
    FAQ = "faq"
    MAINTENANCE = "maintenance"
    CHECKOUT = "checkout"
    BOOKING_INQUIRY = "booking_inquiry"
    UNKNOWN = "unknown"


class TriageResult(BaseModel):
    intent: Intent
    confidence: float
    detected_language: str
    summary: str
    suggested_faq_keys: list[str] = []
