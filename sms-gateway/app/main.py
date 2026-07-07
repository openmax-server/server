from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import load_config
from app.redis_client import close_redis, init_redis
from app.routers import admin, lk, sms
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    await init_redis(config.redis)
    logger.info("Redis подключён: %s", config.redis.url())
    logger.info(
        "Провайдеры: %s | Правил маршрутизации: %d",
        list(config.providers.keys()),
        len(config.routing.rules),
    )
    yield
    await close_redis()
    logger.info("SMS Gateway остановлен")

app = FastAPI(
    title="SMS Gateway",
    description="Маршрутизация SMS по провайдерам в зависимости от страны",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/sms-gateway",
)
app.include_router(sms.router)
app.include_router(lk.router)
app.include_router(admin.router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}