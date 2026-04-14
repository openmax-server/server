from __future__ import annotations
import redis.asyncio as aioredis
from app.config import RedisConfig
_redis: aioredis.Redis | None = None

async def init_redis(cfg: RedisConfig) -> aioredis.Redis:
    global _redis
    _redis = aioredis.from_url(
        cfg.url(),
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis.ping()
    return _redis

async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None

def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis не инициализирован")
    return _redis