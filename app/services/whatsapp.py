import logging

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://graph.facebook.com/v19.0"


class WhatsAppSendError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"WhatsApp API error {status_code}: {detail}")


class WhatsAppClient:
    def __init__(self, phone_number_id: str, access_token: str, test_mode: bool = False) -> None:
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._test_mode = test_mode

    async def send_text(self, to: str, body: str) -> dict:
        if self._test_mode:
            logger.info("[TEST MODE] WA send to %s: %r", to, body[:100])
            return {"messages": [{"id": "mock_msg_id"}]}

        url = f"{_BASE}/{self._phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise WhatsAppSendError(r.status_code, r.text) from exc
        return r.json()

    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        components: list | None = None,
    ) -> dict:
        if self._test_mode:
            logger.info("[TEST MODE] WA template %s to %s", template_name, to)
            return {"messages": [{"id": "mock_tpl_id"}]}

        url = f"{_BASE}/{self._phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or [],
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise WhatsAppSendError(r.status_code, r.text) from exc
        return r.json()
