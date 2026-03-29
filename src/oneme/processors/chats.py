import pydantic
from classes.baseprocessor import BaseProcessor
from oneme.models import ChatSubscribePayloadModel

class ChatsProcessors(BaseProcessor):
    async def chat_subscribe(self, payload, seq, writer):
        # Валидируем входные данные
        try:
            ChatSubscribePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.CHAT_SUBSCRIBE, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Созадаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_SUBSCRIBE, payload=None
        )

        # Отправялем
        await self._send(writer, packet)
