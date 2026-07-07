from __future__ import annotations
from app.config import Config, load_config
from app.providers.registry import build_all_providers
from app.redis_client import get_redis
from app.service import SmsService

_service: SmsService | None = None

def init_service() -> None:
    global _service
    config = load_config()
    providers = build_all_providers(config)
    redis = get_redis()
    _service = SmsService(config, providers, redis)

def get_sms_service() -> SmsService:
    global _service
    if _service is None:
        init_service()
    return _service