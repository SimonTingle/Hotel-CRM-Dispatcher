from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import from_url as redis_from_url
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.rate_limiter import limiter
from app.db.supabase_client import create_supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.redis = await redis_from_url(settings.redis_url, decode_responses=True)
    app.state.supabase = create_supabase_client(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
        test_mode=settings.test_mode,
    )
    yield
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Hotel Dispatcher", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    from app.api.webhook import router as webhook_router
    from app.api.properties import router as properties_router
    from app.api.admin import router as admin_router

    app.include_router(webhook_router, prefix="/webhook")
    app.include_router(properties_router, prefix="/properties")
    app.include_router(admin_router, prefix="/admin")

    @app.get("/healthz", tags=["meta"])
    async def healthz():
        return {"status": "ok"}

    return app


app = create_app()
