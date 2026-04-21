import json
import logging

import httpx

from app.models.triage import Intent, TriageResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a hotel guest communication classifier.
Given a guest message, return ONLY a JSON object (no markdown) with these fields:
- intent: one of "faq", "maintenance", "checkout", "booking_inquiry", "unknown"
- confidence: float 0.0-1.0
- detected_language: ISO 639-1 code (e.g. "en", "es", "fr", "de", "it")
- summary: one sentence in English describing the issue (for ops log, no PII)
- suggested_faq_keys: list of relevant topic keywords if intent is "faq", else []

Property context: {property_context}
Guest message: {message}"""

_FALLBACK = TriageResult(
    intent=Intent.UNKNOWN,
    confidence=0.0,
    detected_language="en",
    summary="Could not classify message",
    suggested_faq_keys=[],
)

_MOCK_RESPONSE = TriageResult(
    intent=Intent.FAQ,
    confidence=0.95,
    detected_language="en",
    summary="Guest asking about wifi password",
    suggested_faq_keys=["wifi", "internet", "password"],
)


class AITriageService:
    def __init__(self, provider: str, api_key: str, test_mode: bool = False) -> None:
        self._provider = provider
        self._api_key = api_key
        self._test_mode = test_mode

    async def classify(self, message: str, property_context: str = "") -> TriageResult:
        if self._test_mode:
            logger.info("[TEST MODE] Triage classify: %r -> %s", message, _MOCK_RESPONSE.intent)
            return _MOCK_RESPONSE

        prompt = _SYSTEM_PROMPT.format(
            property_context=property_context or "N/A",
            message=message,
        )

        try:
            if self._provider == "gemini":
                raw = await self._call_gemini(prompt)
            else:
                raw = await self._call_openai(prompt)
            return self._parse(raw)
        except Exception:
            logger.exception("AI triage failed")
            return _FALLBACK

    async def _call_gemini(self, prompt: str) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={self._api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 256,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    def _parse(self, raw: str) -> TriageResult:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            obj = json.loads(text)
            return TriageResult(
                intent=Intent(obj.get("intent", "unknown")),
                confidence=float(obj.get("confidence", 0.5)),
                detected_language=str(obj.get("detected_language", "en")),
                summary=str(obj.get("summary", "")),
                suggested_faq_keys=list(obj.get("suggested_faq_keys", [])),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            logger.warning("Could not parse AI response: %r", raw[:200])
            return _FALLBACK
