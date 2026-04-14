from __future__ import annotations
import logging
import random
import uuid
from app.config import ProviderConfig
from app.providers import SendResult
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

class LkApiProvider(BaseProvider):
    """
    Внутренний провайдер — SMS не шлёт.
    Генерирует код, который отображается в личном кабинете.
    Используется для всех стран кроме России.
    """
    name = "lk_api"

    def __init__(self, config: ProviderConfig | None = None) -> None:
        pass

    async def send(self, phone_number: str, code: str | None = None) -> SendResult:
        normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        if not code:
            code = str(random.randint(10000, 99999))
        request_uuid = str(uuid.uuid4())
        logger.info(
            "lk_api: код для ЛК | phone=%s code=%s uuid=%s",
            normalized, code, request_uuid,
        )
        return SendResult(
            success=True,
            provider=self.name,
            code=code,
            raw_response={"code": int(code), "uuid": request_uuid, "note": "displayed in personal cabinet"},
        )