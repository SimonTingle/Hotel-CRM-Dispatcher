import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from app.api.deps import get_supabase
from app.core.security import get_admin_api_key
from app.models.property import (
    CrewContactCreate,
    FAQEntryCreate,
    Property,
    PropertyCreate,
    PropertyUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["properties"], dependencies=[Depends(get_admin_api_key)])


@router.post("", status_code=201)
async def create_property(
    body: PropertyCreate,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    row = {
        "name": body.name,
        "address": body.address,
        "checkin_time": str(body.checkin_time) if body.checkin_time else None,
        "checkout_time": str(body.checkout_time) if body.checkout_time else None,
    }
    if body.wifi_password:
        row["wifi_password_enc"] = body.wifi_password  # encrypt at DB level via trigger or RPC
    r = await supabase.table("properties").insert(row).execute()
    return r.data[0]


@router.get("")
async def list_properties(supabase: AsyncClient = Depends(get_supabase)) -> list[dict]:
    r = await supabase.table("properties").select("*").is_("deleted_at", "null").execute()
    return r.data or []


@router.get("/{property_id}")
async def get_property(
    property_id: UUID,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    r = await supabase.table("properties").select("*").eq("id", str(property_id)).single().execute()
    if not r.data:
        raise HTTPException(404, "Property not found")
    prop = r.data

    faqs = await supabase.table("faq_entries").select("*").eq("property_id", str(property_id)).execute()
    crew = await supabase.table("crew_contacts").select("*").eq("property_id", str(property_id)).execute()
    prop["faq_entries"] = faqs.data or []
    prop["crew_contacts"] = crew.data or []
    return prop


@router.put("/{property_id}")
async def update_property(
    property_id: UUID,
    body: PropertyUpdate,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    updates = body.model_dump(exclude_none=True)
    if "wifi_password" in updates:
        updates["wifi_password_enc"] = updates.pop("wifi_password")
    if not updates:
        raise HTTPException(400, "No fields to update")
    r = await supabase.table("properties").update(updates).eq("id", str(property_id)).execute()
    return r.data[0]


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: UUID,
    supabase: AsyncClient = Depends(get_supabase),
) -> None:
    from datetime import datetime, timezone
    await supabase.table("properties").update(
        {"deleted_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", str(property_id)).execute()


# --- FAQ entries ---

@router.post("/{property_id}/faqs", status_code=201)
async def add_faq(
    property_id: UUID,
    body: FAQEntryCreate,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    row = {
        "property_id": str(property_id),
        "language": body.language,
        "question": body.question,
        "answer": body.answer,
        "tags": body.tags,
    }
    r = await supabase.table("faq_entries").insert(row).execute()
    return r.data[0]


@router.put("/{property_id}/faqs/{faq_id}")
async def update_faq(
    property_id: UUID,
    faq_id: UUID,
    body: FAQEntryCreate,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    r = await supabase.table("faq_entries").update(body.model_dump()).eq(
        "id", str(faq_id)
    ).eq("property_id", str(property_id)).execute()
    if not r.data:
        raise HTTPException(404, "FAQ entry not found")
    return r.data[0]


@router.delete("/{property_id}/faqs/{faq_id}", status_code=204)
async def delete_faq(
    property_id: UUID,
    faq_id: UUID,
    supabase: AsyncClient = Depends(get_supabase),
) -> None:
    await supabase.table("faq_entries").delete().eq("id", str(faq_id)).eq(
        "property_id", str(property_id)
    ).execute()


# --- Crew contacts ---

@router.post("/{property_id}/crew", status_code=201)
async def add_crew(
    property_id: UUID,
    body: CrewContactCreate,
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    if body.role not in ("cleaning", "maintenance", "manager"):
        raise HTTPException(400, "role must be cleaning, maintenance, or manager")
    row = {
        "property_id": str(property_id),
        "name": body.name,
        "role": body.role,
        "whatsapp_number": body.whatsapp_number,
    }
    r = await supabase.table("crew_contacts").insert(row).execute()
    return r.data[0]


@router.delete("/{property_id}/crew/{crew_id}", status_code=204)
async def delete_crew(
    property_id: UUID,
    crew_id: UUID,
    supabase: AsyncClient = Depends(get_supabase),
) -> None:
    await supabase.table("crew_contacts").delete().eq("id", str(crew_id)).eq(
        "property_id", str(property_id)
    ).execute()
