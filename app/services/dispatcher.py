import logging
from datetime import datetime, timezone

from supabase._async.client import AsyncClient

from app.models.session import GuestSession
from app.models.triage import Intent, TriageResult
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)

_ROLE_FOR_INTENT = {
    Intent.MAINTENANCE: "maintenance",
    Intent.CHECKOUT: "cleaning",
    Intent.UNKNOWN: "manager",
}

_INTENT_LABEL = {
    Intent.MAINTENANCE: "MAINTENANCE REQUEST",
    Intent.CHECKOUT: "CHECKOUT NOTIFICATION",
    Intent.UNKNOWN: "ESCALATION — UNCLASSIFIED",
}


class DispatcherService:
    def __init__(
        self,
        wa_client: WhatsAppClient,
        supabase: AsyncClient,
        ops_group_id: str,
    ) -> None:
        self._wa = wa_client
        self._supabase = supabase
        self._ops_group_id = ops_group_id

    async def dispatch(
        self,
        triage: TriageResult,
        session: GuestSession,
        escalate: bool = False,
    ) -> None:
        property_name = await self._get_property_name(session.property_id)
        crew = await self._get_crew(session.property_id, triage.intent)

        masked_wa = _mask_number(session.guest_wa_id)
        label = _INTENT_LABEL.get(triage.intent, "ALERT")
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")

        lines = [
            f"[{label}]",
            f"Property: {property_name}",
            f"Guest: {masked_wa}",
            f"Issue: {triage.summary}",
            f"Time: {now}",
        ]

        if crew:
            lines.append(f"Assigned to: {crew['name']} ({crew['role'].title()}) — {crew['whatsapp_number']}")

        if escalate:
            lines.append("⚠️ Could not auto-classify — please review.")

        message = "\n".join(lines)

        try:
            await self._wa.send_text(self._ops_group_id, message)
        except Exception:
            logger.exception("Failed to dispatch to ops group")

        try:
            await self._supabase.table("guest_messages").insert({
                "guest_wa_id": session.guest_wa_id,
                "property_id": session.property_id,
                "direction": "outbound",
                "intent": triage.intent.value,
                "message_scrubbed": message,
            }).execute()
        except Exception:
            logger.exception("Failed to log dispatch message")

    async def _get_property_name(self, property_id: str | None) -> str:
        if not property_id:
            return "Unknown Property"
        try:
            r = (
                await self._supabase
                .table("properties")
                .select("name")
                .eq("id", property_id)
                .single()
                .execute()
            )
            return r.data["name"] if r.data else "Unknown Property"
        except Exception:
            return "Unknown Property"

    async def _get_crew(self, property_id: str | None, intent: Intent) -> dict | None:
        if not property_id:
            return None
        role = _ROLE_FOR_INTENT.get(intent, "manager")
        try:
            r = (
                await self._supabase
                .table("crew_contacts")
                .select("name, role, whatsapp_number")
                .eq("property_id", property_id)
                .eq("role", role)
                .limit(1)
                .execute()
            )
            return r.data[0] if r.data else None
        except Exception:
            return None


def _mask_number(wa_id: str) -> str:
    if len(wa_id) >= 4:
        return f"+{'*' * (len(wa_id) - 4)}{wa_id[-4:]}"
    return "****"
