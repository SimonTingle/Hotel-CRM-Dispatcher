import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.core.gdpr import get_session_ttl
from app.models.session import GuestSession


class SessionManager:
    def __init__(self, redis: Redis, ttl_hours: int = 24) -> None:
        self._redis = redis
        self._ttl_hours = ttl_hours

    def _key(self, wa_id: str) -> str:
        return f"session:{wa_id}"

    async def get(self, wa_id: str) -> GuestSession | None:
        raw = await self._redis.get(self._key(wa_id))
        if raw is None:
            return None
        return GuestSession.model_validate_json(raw)

    async def set(self, session: GuestSession) -> None:
        ttl = get_session_ttl(session.checkout_date, self._ttl_hours)
        await self._redis.setex(
            self._key(session.guest_wa_id),
            ttl,
            session.model_dump_json(),
        )

    async def update_language(self, wa_id: str, lang: str) -> None:
        session = await self.get(wa_id)
        if session:
            session.detected_language = lang
            session.updated_at = datetime.now(timezone.utc)
            await self.set(session)

    async def delete(self, wa_id: str) -> None:
        await self._redis.delete(self._key(wa_id))
        await self._redis.delete(f"gdpr:purge:{wa_id}")
