from fastapi import Request
from redis.asyncio import Redis
from supabase._async.client import AsyncClient


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_supabase(request: Request) -> AsyncClient:
    return request.app.state.supabase
