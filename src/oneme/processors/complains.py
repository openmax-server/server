import pydantic
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import ComplainReasonsGetPayloadModel

class ComplainsProcessors(BaseProcessor):
    async def complain_reasons_get(self, payload, seq, writer):
        """Обработчик получения причин жалоб"""
        # Валидируем данные пакета
        try:
            ComplainReasonsGetPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.COMPLAIN_REASONS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Собираем данные пакета
        payload = {
            "complains": self.static.COMPLAIN_REASONS,
            "complainSync": int(time.time())
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.opcodes.COMPLAIN_REASONS_GET, payload=payload
        )

        # Отправляем пакет
        await self._send(writer, packet)
