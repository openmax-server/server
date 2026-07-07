from __future__ import annotations
from abc import ABC, abstractmethod
from app.providers import SendResult

class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def send(self, phone_number: str, code: str | None = None) -> SendResult:
        pass