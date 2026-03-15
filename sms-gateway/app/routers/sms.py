from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import get_sms_service
from app.service import RateLimitExceeded, SmsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sms", tags=["SMS"])

class SendCodeRequest(BaseModel):
    phone_number: str

class SendCodeResponse(BaseModel):
    success: bool
    provider: str
    phone_number: str
    code: str | None = None
    error: str | None = None

@router.post("/send", response_model=SendCodeResponse)
async def send_code(
    request: SendCodeRequest,
    service: SmsService = Depends(get_sms_service),
) -> SendCodeResponse:
    try:
        result = await service.send_code(request.phone_number)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail={"error": "Слишком много запросов для этого номера", "retry_after": e.retry_after},
            headers={"Retry-After": str(e.retry_after)},
        )
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Ошибка отправки SMS")
    return SendCodeResponse(
        success=True,
        provider=result.provider,
        phone_number=request.phone_number,
        code=result.code,
    )