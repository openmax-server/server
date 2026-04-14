import pydantic
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import AssetsPayloadModel

class AssetsProcessors(BaseProcessor):
    async def assets_update(self, payload, seq, writer):
        """Обработчик запроса ассетов клиента на сервере"""
        # Валидируем данные пакета
        try:
            AssetsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: сейчас это заглушка, а попозже нужно сделать полноценную реализацию

        # Данные пакета
        payload = {
            "sections": [],
            "sync": int(time.time() * 1000)
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_UPDATE, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)