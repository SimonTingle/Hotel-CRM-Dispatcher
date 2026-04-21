import logging

from supabase._async.client import AsyncClient

from app.models.triage import TriageResult
from app.services.ai_triage import AITriageService

logger = logging.getLogger(__name__)

_FALLBACK_REPLY = {
    "en": "I'll connect you with our team right away. Please hold on.",
    "es": "Te conectaré con nuestro equipo ahora mismo. Por favor, espera.",
    "fr": "Je vous mets en contact avec notre équipe immédiatement. Veuillez patienter.",
    "de": "Ich verbinde Sie sofort mit unserem Team. Bitte warten Sie.",
    "it": "La metto subito in contatto con il nostro team. Attenda, per favore.",
}

_REPLY_PROMPT = """You are a helpful hotel concierge. Answer the guest's question using ONLY the FAQ content below.
Reply in the language with ISO code: {language}.
Be concise and friendly. If the FAQ doesn't fully answer the question, say so politely.

FAQ entries:
{faq_content}

Guest question: {question}"""


class FAQEngine:
    def __init__(self, supabase: AsyncClient, triage_service: AITriageService) -> None:
        self._supabase = supabase
        self._triage = triage_service

    async def answer(
        self,
        property_id: str | None,
        triage: TriageResult,
        original_message: str,
    ) -> str:
        fallback = _FALLBACK_REPLY.get(triage.detected_language, _FALLBACK_REPLY["en"])

        if not property_id:
            return fallback

        try:
            result = (
                await self._supabase
                .table("faq_entries")
                .select("question, answer, tags")
                .eq("property_id", property_id)
                .eq("language", triage.detected_language)
                .execute()
            )
            entries = result.data or []

            # Tag overlap filter in Python (Supabase JS client doesn't expose && easily)
            keys = set(triage.suggested_faq_keys)
            if keys:
                scored = [
                    (e, len(keys & set(e.get("tags", []))))
                    for e in entries
                ]
                scored.sort(key=lambda x: x[1], reverse=True)
                matched = [e for e, score in scored[:3] if score > 0]
            else:
                matched = entries[:3]

            if not matched:
                # Try English fallback entries
                if triage.detected_language != "en":
                    result_en = (
                        await self._supabase
                        .table("faq_entries")
                        .select("question, answer, tags")
                        .eq("property_id", property_id)
                        .eq("language", "en")
                        .execute()
                    )
                    matched = (result_en.data or [])[:3]

            if not matched:
                return fallback

            faq_content = "\n\n".join(
                f"Q: {e['question']}\nA: {e['answer']}" for e in matched
            )
            prompt = _REPLY_PROMPT.format(
                language=triage.detected_language,
                faq_content=faq_content,
                question=original_message,
            )
            reply = await self._triage._call_gemini(prompt) if self._triage._provider == "gemini" \
                else await self._triage._call_openai(prompt)
            return reply.strip()

        except Exception:
            logger.exception("FAQ engine failed")
            return fallback
