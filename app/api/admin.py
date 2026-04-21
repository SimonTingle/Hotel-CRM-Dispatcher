import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from supabase._async.client import AsyncClient

from app.api.deps import get_redis, get_supabase
from app.core.security import get_admin_api_key
from app.services.session_manager import SessionManager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"], dependencies=[Depends(get_admin_api_key)])


@router.get("/health")
async def health(
    redis: Redis = Depends(get_redis),
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    redis_ok = False
    supabase_ok = False

    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    try:
        await supabase.table("properties").select("id").limit(1).execute()
        supabase_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if (redis_ok and supabase_ok) else "degraded",
        "redis": "ok" if redis_ok else "error",
        "supabase": "ok" if supabase_ok else "error",
    }


@router.get("/metrics")
async def metrics(supabase: AsyncClient = Depends(get_supabase)) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    r = (
        await supabase
        .table("guest_messages")
        .select("intent")
        .gte("created_at", since)
        .eq("direction", "inbound")
        .execute()
    )
    counts: dict[str, int] = {}
    for row in r.data or []:
        intent = row.get("intent") or "unknown"
        counts[intent] = counts.get(intent, 0) + 1
    return {"period": "last_24h", "counts": counts}


@router.post("/purge/{wa_id}", status_code=204)
async def gdpr_purge(
    wa_id: str,
    redis: Redis = Depends(get_redis),
    supabase: AsyncClient = Depends(get_supabase),
) -> None:
    settings = get_settings()
    sessions = SessionManager(redis, settings.redis_session_ttl_hours)
    await sessions.delete(wa_id)

    try:
        await supabase.table("guest_messages").delete().eq("guest_wa_id", wa_id).execute()
    except Exception:
        logger.exception("Failed to purge Supabase rows for %s", wa_id)
