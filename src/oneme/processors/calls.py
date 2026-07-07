import pydantic
import secrets
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import (
    GetCallTokenPayloadModel, 
    GetCallHistoryPayloadModel
)

class CallsProcessors(BaseProcessor):
    async def ok_token(self, payload, seq, writer):
        """Получение токена для звонка"""
        # Валидируем данные пакета
        try:
            GetCallTokenPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.OK_TOKEN, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: когда-то взяться за звонки

        # Данные пакета
        payload = {
            "token": secrets.token_urlsafe(128),
            "token_lifetime_ts": int(time.time() * 1000),
            "token_refresh_ts": int(time.time() * 1000)
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.OK_TOKEN, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def video_chat_history(self, payload, seq, writer):
        """Обработчик получения истории звонков"""
        # Валидируем данные пакета
        try:
            GetCallHistoryPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.VIDEO_CHAT_HISTORY, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: сейчас это заглушка, а попозже нужно сделать полноценную реализацию

        # Данные пакета
        payload = {
            "hasMore": False,
            "history": [],
            "backwardMarker": 0,
            "forwardMarker": 0
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.VIDEO_CHAT_HISTORY, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)