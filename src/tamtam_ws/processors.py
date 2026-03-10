import hashlib, secrets, random, time, logging, json
from common.static import Static
from common.tools import Tools
from tamtam_ws.proto import Proto
from tamtam_ws.models import *

class Processors:
    def __init__(self, db_pool=None, clients={}, send_event=None):
        self.static = Static()
        self.tools = Tools()
        self.proto = Proto()
        self.error_types = self.static.ErrorTypes()
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def _send(self, writer, packet):
        """Отправка пакета"""
        try:
            await writer.send(packet)
        except Exception as error:
            self.logger.error(f"Ошибка при отправке пакета - {error}")

    async def _send_error(self, seq, opcode, type, writer):
        payload = self.static.ERROR_TYPES.get(type, {
            "localizedMessage": "Неизвестная ошибка",
            "error": "unknown.error",
            "message": "Unknown error",
            "title": "Неизвестная ошибка"
        })
        
        packet = self.proto.pack_packet(
            seq=seq, opcode=opcode, payload=payload
        )
        
        await self._send(writer, packet)

    async def process_hello(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.SESSION_INIT, self.error_types.INVALID_PAYLOAD, writer)
            return None, None

        # Получаем данные из пакета
        deviceType = payload.get("userAgent").get("deviceType")
        deviceName = payload.get("userAgent").get("deviceName")

        # Собираем данные ответа
        payload = {
            "proxy": "",
            "logs-enabled": False,
            "proxy-domains": [],
            "location": "RU"
        }

        # Создаем пакет
        packet = self.proto.pack_packet(seq=seq, opcode=self.proto.SESSION_INIT, payload=payload)

        # Отправляем
        await self._send(writer, packet)
        return deviceType, deviceName
        
    async def process_ping(self, payload, seq, writer):
        """Обработчик пинга"""
        # Создаем пакет
        packet = self.proto.pack_packet(seq=seq, opcode=self.proto.PING)

        # Отправляем
        await self._send(writer, packet)

    async def process_telemetry(self, payload, seq, writer):
        """Обработчик телеметрии"""
        # Создаем пакет
        packet = self.proto.pack_packet(seq=seq, opcode=self.proto.LOG)

        # Отправляем
        await self._send(writer, packet)
