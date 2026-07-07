from __future__ import annotations
import logging
import redis.asyncio as aioredis
from app.config import Config
from app.providers import SendResult
from app.providers.base import BaseProvider
logger = logging.getLogger(__name__)
RATE_KEY = "sms:rate:{phone}"
CODE_KEY = "sms:code:{phone}"

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")

class SmsService:
    def __init__(self, config: Config, providers: dict[str, BaseProvider], redis: aioredis.Redis) -> None:
        self.config = config
        self.providers = providers
        self.redis = redis

    async def send_code(self, phone_number: str, code: str | None = None) -> SendResult:
        normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        await self._check_rate_limit(normalized)
        primary_name, fallback_name = self.config.resolve_provider(normalized)
        result = await self._try_send(primary_name, normalized, code=code)
        if not result.success and fallback_name:
            logger.warning(
                "Провайдер %s недоступен для %s, пробуем fallback: %s",
                primary_name, normalized, fallback_name,
            )
            result = await self._try_send(fallback_name, normalized, code=code)
        if result.success and result.code:
            ttl = self.config.settings.code_ttl_seconds
            key = CODE_KEY.format(phone=normalized)
            await self.redis.set(key, result.code, ex=ttl)
            if self.config.settings.log_codes:
                logger.info("Код сохранён: phone=%s code=%s provider=%s", normalized, result.code, result.provider)
        return result

    async def _check_rate_limit(self, phone: str) -> None:
        rl = self.config.settings.rate_limit
        if not rl.enabled:
            return
        key = RATE_KEY.format(phone=phone)
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
        if count == 1:
            await self.redis.expire(key, rl.window_seconds)
            ttl = rl.window_seconds
        if count > rl.max_attempts:
            retry_after = ttl if ttl > 0 else rl.window_seconds
            logger.warning("Rate limit для %s: попытка %d/%d, retry_after=%ds", phone, count, rl.max_attempts, retry_after)
            raise RateLimitExceeded(retry_after=retry_after)

    async def _try_send(self, provider_name: str, phone: str, code: str | None = None) -> SendResult:
        provider = self.providers.get(provider_name)
        if provider is None:
            logger.error("Провайдер не найден: %s", provider_name)
            return SendResult(success=False, provider=provider_name, error=f"Provider '{provider_name}' not found")
        return await provider.send(phone, code=code)

    async def get_pending_code(self, phone_number: str) -> str | None:
        normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        key = CODE_KEY.format(phone=normalized)
        return await self.redis.get(key)

    async def consume_code(self, phone_number: str) -> str | None:
        normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        key = CODE_KEY.format(phone=normalized)
        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        code, _ = await pipe.execute()
        return code

    async def list_pending_codes(self) -> list[dict]:
        pattern = CODE_KEY.format(phone="*")
        result = []
        async for key in self.redis.scan_iter(pattern):
            pipe = self.redis.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            code, ttl = await pipe.execute()
            if code:
                phone = key.replace("sms:code:", "")
                result.append({"phone": phone, "code": code, "expires_in": max(ttl, 0)})
        return result