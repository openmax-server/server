from __future__ import annotations
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.config import reload_config
from app.deps import get_sms_service, init_service
from app.service import SmsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

class RoutingInfo(BaseModel):
    phone: str
    primary_provider: str
    fallback_provider: str | None

@router.post("/reload", response_model=dict)
async def reload() -> dict:
    """Перечитать config.yaml без перезапуска сервиса."""
    new_config = reload_config()
    init_service()
    providers = list(new_config.providers.keys())
    rules_count = len(new_config.routing.rules)
    logger.info("Конфиг перезагружен: провайдеры=%s правил=%d", providers, rules_count)
    return {"success": True, "providers": providers, "routing_rules": rules_count}

@router.get("/routing/resolve", response_model=RoutingInfo)
async def resolve_routing(
    phone: str,
    service: SmsService = Depends(get_sms_service),
) -> RoutingInfo:
    """Проверить, какой провайдер будет выбран для номера."""
    primary, fallback = service.config.resolve_provider(phone)
    return RoutingInfo(phone=phone, primary_provider=primary, fallback_provider=fallback)

@router.get("/routing/rules", response_model=list[dict])
async def list_rules(
    service: SmsService = Depends(get_sms_service),
) -> list[dict]:
    """Список всех правил маршрутизации."""
    return [rule.model_dump() for rule in service.config.routing.rules]

@router.get("/providers", response_model=list[dict])
async def list_providers(
    service: SmsService = Depends(get_sms_service),
) -> list[dict]:
    """Список активных провайдеров."""
    return [
        {"name": name, "type": name, "enabled": True}
        for name in service.providers.keys()
    ]