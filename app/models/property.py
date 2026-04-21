from datetime import time
from uuid import UUID

from pydantic import BaseModel


class FAQEntry(BaseModel):
    id: UUID
    property_id: UUID
    language: str
    question: str
    answer: str
    tags: list[str] = []


class FAQEntryCreate(BaseModel):
    language: str
    question: str
    answer: str
    tags: list[str] = []


class CrewContact(BaseModel):
    id: UUID
    property_id: UUID
    name: str
    role: str
    whatsapp_number: str


class CrewContactCreate(BaseModel):
    name: str
    role: str
    whatsapp_number: str


class Property(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    checkin_time: time | None = None
    checkout_time: time | None = None
    crew_contacts: list[CrewContact] = []
    faq_entries: list[FAQEntry] = []


class PropertyCreate(BaseModel):
    name: str
    address: str | None = None
    checkin_time: time | None = None
    checkout_time: time | None = None
    wifi_password: str = ""


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    checkin_time: time | None = None
    checkout_time: time | None = None
    wifi_password: str | None = None
