from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    type: str
    enabled: bool = True
    model_config = {"extra": "allow"}

    def extra(self) -> dict[str, Any]:
        return dict(self.__pydantic_extra__) if self.__pydantic_extra__ else {}

class RoutingRule(BaseModel):
    name: str
    prefixes: list[str]
    provider: str
    fallback: str | None = None

    def matches(self, phone: str) -> bool:
        normalized = phone if phone.startswith("+") else f"+{phone}"
        for prefix in sorted(self.prefixes, key=len, reverse=True):
            if normalized.startswith(prefix):
                return True
        return False

class RoutingConfig(BaseModel):
    rules: list[RoutingRule] = []
    default_provider: str = "lk_api"
    default_fallback: str | None = None

class RateLimitSettings(BaseModel):
    enabled: bool = True
    max_attempts: int = 3
    window_seconds: int = 600

class AppSettings(BaseModel):
    log_codes: bool = True
    code_ttl_seconds: int = 300
    rate_limit: RateLimitSettings = RateLimitSettings()

class RedisConfig(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None

    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

class Config(BaseModel):
    providers: dict[str, ProviderConfig]
    routing: RoutingConfig
    settings: AppSettings = AppSettings()
    redis: RedisConfig = RedisConfig()

    def resolve_provider(self, phone: str) -> tuple[str, str | None]:
        for rule in self.routing.rules:
            if rule.matches(phone):
                return rule.provider, rule.fallback
        return self.routing.default_provider, self.routing.default_fallback

@lru_cache(maxsize=1)
def load_config() -> Config:
    path = Path(os.getenv("CONFIG_PATH", "config.yaml"))
    if not path.exists():
        raise FileNotFoundError(f"Конфиг не найден: {path}")
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)

def reload_config() -> Config:
    load_config.cache_clear()
    return load_config()