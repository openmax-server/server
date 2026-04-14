from __future__ import annotations
import logging
from app.config import Config, ProviderConfig
from app.providers.base import BaseProvider
from app.providers.lk_api import LkApiProvider
from app.providers.sms_api import SmsApiProvider

logger = logging.getLogger(__name__)
PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "sms_api": SmsApiProvider,
    "lk_api": LkApiProvider,
}

def build_provider(name: str, config: ProviderConfig) -> BaseProvider | None:
    cls = PROVIDER_REGISTRY.get(config.type)
    if cls is None:
        logger.error("Неизвестный тип провайдера: %s", config.type)
        return None
    if not config.enabled:
        logger.debug("Провайдер %s отключён", name)
        return None
    return cls(config)

def build_all_providers(config: Config) -> dict[str, BaseProvider]:
    result: dict[str, BaseProvider] = {}
    for name, provider_cfg in config.providers.items():
        provider = build_provider(name, provider_cfg)
        if provider is not None:
            result[name] = provider
            logger.info("Провайдер загружен: %s (тип: %s)", name, provider_cfg.type)
    if "lk_api" not in result:
        result["lk_api"] = LkApiProvider()
        logger.info("lk_api добавлен как fallback по умолчанию")
    return result