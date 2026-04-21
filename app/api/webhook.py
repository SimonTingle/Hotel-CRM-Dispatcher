import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis
from supabase._async.client import AsyncClient

from app.api.deps import get_redis, get_supabase
from app.config import Settings, get_settings
from app.core.gdpr import scrub_pii
from app.core.rate_limiter import WEBHOOK_LIMIT, limiter
from app.core.security import require_hmac
from app.models.session import GuestSession
from app.models.triage import Intent
from app.models.webhook import WAWebhookPayload
from app.services.ai_triage import AITriageService
from app.services.dispatcher import DispatcherService
from app.services.faq_engine import FAQEngine
from app.services.session_manager import SessionManager
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    if hub_mode == "subscribe" and hmac.compare_digest(
        hub_verify_token,
        settings.wa_verify_token.get_secret_value(),
    ):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp", dependencies=[Depends(require_hmac)])
@limiter.limit(WEBHOOK_LIMIT)
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    supabase: AsyncClient = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    # Use cached raw body from require_hmac dependency
    body = getattr(request.state, "raw_body", await request.body())
    payload = WAWebhookPayload.model_validate_json(body)

    for entry in payload.entry:
        for change in entry.changes:
            for message in change.value.messages:
                if message.type != "text" or message.text is None:
                    continue

                # Idempotency guard
                idem_key = f"processed:{message.id}"
                if await redis.set(idem_key, "1", ex=3600, nx=True) is None:
                    logger.info("Duplicate message %s, skipping", message.id)
                    continue

                contact = next(
                    (c for c in change.value.contacts if c.wa_id == message.from_),
                    None,
                )
                guest_name = contact.profile.name if contact else "Guest"

                background_tasks.add_task(
                    process_message,
                    wa_id=message.from_,
                    message_id=message.id,
                    message_text=message.text.body,
                    guest_name=guest_name,
                    redis=redis,
                    supabase=supabase,
                    settings=settings,
                )

    return {"status": "ok"}


async def process_message(
    wa_id: str,
    message_id: str,
    message_text: str,
    guest_name: str,
    redis: Redis,
    supabase: AsyncClient,
    settings: Settings,
) -> None:
    sessions = SessionManager(redis, settings.redis_session_ttl_hours)

    session = await sessions.get(wa_id)
    if session is None:
        session = GuestSession(
            guest_wa_id=wa_id,
            guest_name=guest_name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    clean_text = scrub_pii(message_text)

    property_context = ""
    if session.property_id:
        cached = await redis.get(f"prop_cache:{session.property_id}")
        if cached:
            property_context = cached

    triage = AITriageService(
        provider=settings.ai_provider,
        api_key=(
            settings.gemini_api_key.get_secret_value()
            if settings.ai_provider == "gemini"
            else settings.openai_api_key.get_secret_value()
        ),
        test_mode=settings.test_mode,
    )
    result = await triage.classify(clean_text, property_context)

    # Log scrubbed message
    try:
        await supabase.table("guest_messages").insert({
            "guest_wa_id": wa_id,
            "property_id": session.property_id,
            "direction": "inbound",
            "intent": result.intent.value,
            "message_scrubbed": clean_text,
        }).execute()
    except Exception:
        logger.exception("Failed to log guest message")

    wa_client = WhatsAppClient(
        phone_number_id=settings.wa_phone_number_id,
        access_token=settings.wa_access_token.get_secret_value(),
        test_mode=settings.test_mode,
    )

    if result.intent == Intent.FAQ:
        faq = FAQEngine(supabase=supabase, triage_service=triage)
        reply = await faq.answer(session.property_id, result, message_text)
        await wa_client.send_text(wa_id, reply)

    elif result.intent in (Intent.MAINTENANCE, Intent.CHECKOUT):
        dispatcher = DispatcherService(
            wa_client=wa_client,
            supabase=supabase,
            ops_group_id=settings.ops_whatsapp_group_id,
        )
        await dispatcher.dispatch(result, session)
        ack = _ops_ack(result.intent, result.detected_language)
        await wa_client.send_text(wa_id, ack)

    elif result.intent == Intent.BOOKING_INQUIRY:
        await wa_client.send_text(
            wa_id,
            _booking_reply(result.detected_language),
        )

    else:
        dispatcher = DispatcherService(
            wa_client=wa_client,
            supabase=supabase,
            ops_group_id=settings.ops_whatsapp_group_id,
        )
        await dispatcher.dispatch(result, session, escalate=True)

    session.message_count += 1
    session.last_intent = result.intent
    session.detected_language = result.detected_language
    session.updated_at = datetime.now(timezone.utc)
    await sessions.set(session)


def _ops_ack(intent: Intent, lang: str) -> str:
    msgs = {
        Intent.MAINTENANCE: {
            "es": "Gracias por avisarnos. Nuestro equipo lo atenderá en breve.",
            "en": "Thank you for letting us know. Our team will attend to this shortly.",
            "fr": "Merci de nous avoir prévenus. Notre équipe s'en occupera bientôt.",
            "de": "Danke für die Information. Unser Team kümmert sich bald darum.",
            "it": "Grazie per averci informato. Il nostro team se ne occuperà a breve.",
        },
        Intent.CHECKOUT: {
            "es": "¡Gracias por su estancia! Hemos notificado al equipo de limpieza.",
            "en": "Thank you for your stay! We've notified the cleaning team.",
            "fr": "Merci pour votre séjour ! Nous avons informé l'équipe de nettoyage.",
            "de": "Danke für Ihren Aufenthalt! Wir haben das Reinigungsteam benachrichtigt.",
            "it": "Grazie per il suo soggiorno! Abbiamo avvisato il team delle pulizie.",
        },
    }
    return msgs.get(intent, {}).get(lang, msgs[intent]["en"])


def _booking_reply(lang: str) -> str:
    msgs = {
        "es": "Para reservas, por favor contáctenos a través de la plataforma donde realizó su reserva.",
        "en": "For bookings, please contact us through the platform where you made your reservation.",
        "fr": "Pour les réservations, veuillez nous contacter via la plateforme où vous avez réservé.",
        "de": "Für Buchungen wenden Sie sich bitte an die Plattform, über die Sie gebucht haben.",
        "it": "Per le prenotazioni, la preghiamo di contattarci tramite la piattaforma dove ha effettuato la prenotazione.",
    }
    return msgs.get(lang, msgs["en"])
