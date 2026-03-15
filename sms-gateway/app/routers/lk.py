from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.deps import get_sms_service
from app.service import SmsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lk", tags=["Личный кабинет"])

class PendingCode(BaseModel):
    phone: str
    code: str
    expires_in: int

@router.get("/codes", response_model=list[PendingCode])
async def list_codes(
    service: SmsService = Depends(get_sms_service),
) -> list[PendingCode]:
    items = await service.list_pending_codes()
    return [PendingCode(**item) for item in items]

@router.get("/code", response_model=PendingCode)
async def get_code(
    phone: str = Query(..., description="Номер телефона"),
    service: SmsService = Depends(get_sms_service),
) -> PendingCode:
    items = await service.list_pending_codes()
    normalized = phone if phone.startswith("+") else f"+{phone}"
    for item in items:
        if item["phone"] == normalized:
            return PendingCode(**item)
    raise HTTPException(status_code=404, detail="Код не найден или истёк")

@router.delete("/code", response_model=dict)
async def consume_code(
    phone: str = Query(..., description="Номер телефона"),
    service: SmsService = Depends(get_sms_service),
) -> dict:
    code = await service.consume_code(phone)
    if code is None:
        raise HTTPException(status_code=404, detail="Код не найден или истёк")
    return {"success": True, "phone": phone, "consumed_code": code}