import pydantic
from classes.baseprocessor import BaseProcessor
from tamtam.models import HelloPayloadModel, PingPayloadModel

class MainProcessors(BaseProcessor):
    async def session_init(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            await self._send_error(seq, self.opcodes.SESSION_INIT,
                                   self.error_types.INVALID_PAYLOAD, writer)
            return None, None

        # Получаем данные из пакета
        device_type = payload.get("userAgent").get("deviceType")
        device_name = payload.get("userAgent").get("deviceName")

        # Данные пакета
        payload = {
            "proxy": "",
            "logs-enabled": False,
            "proxy-domains": [],
            "location": "RU",
            "libh-enabled": False,
            "phone-auto-complete-enabled": False
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSION_INIT, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return device_type, device_name
    
    async def ping(self, payload, seq, writer):
        """Обработчик пинга"""
        # Валидируем данные пакета
        try:
            PingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.PING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.PING, payload=None
        )

        # Отправляем
        await self._send(writer, packet)

    async def log(self, payload, seq, writer):
        """Обработчик лога"""
        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOG, payload=None
        )

        # Отправляем
        await self._send(writer, packet)