from __future__ import annotations
import logging
import httpx
from app.config import ProviderConfig
from app.providers import SendResult
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

class SmsApiProvider(BaseProvider):
    """
    Внешний SMS-сервис.
    Отправляет реальное SMS, возвращает код и uuid.
    Используется для России (+7).
    """
    name = "sms_api"

    def __init__(self, config: ProviderConfig) -> None:
        extra = config.extra()
        self.base_url: str = extra.get("base_url", "").rstrip("/")
        self.send_endpoint: str = extra.get("send_endpoint", "/auth/code")
        self.timeout: int = int(extra.get("timeout", 10))

    async def send(self, phone_number: str, code: str | None = None) -> SendResult:
        normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        url = f"{self.base_url}{self.send_endpoint}"
        payload: dict = {"phone_number": normalized}
        if code:
            payload["code"] = code
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"accept": "application/json", "Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            code = str(data.get("code", ""))
            logger.info("sms_api: SMS отправлен на %s | uuid=%s code=%s", normalized, data.get("uuid"), code)
            return SendResult(
                success=True,
                provider=self.name,
                code=code,
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            logger.error("sms_api HTTP %s для %s: %s", e.response.status_code, normalized, e)
            return SendResult(success=False, provider=self.name, error=str(e))
        except Exception as e:
            logger.error("sms_api ошибка для %s: %s", normalized, e)
            return SendResult(success=False, provider=self.name, error=str(e))