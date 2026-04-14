from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class SendResult:
    success: bool
    provider: str
    code: str | None = None
    raw_response: dict = field(default_factory=dict)
    error: str | None = None