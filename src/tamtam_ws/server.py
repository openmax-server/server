import asyncio, logging, json
from websockets.asyncio.server import serve
from tamtam_ws.models import *
from pydantic import ValidationError
from tamtam_ws.proto import Proto
from tamtam_ws.processors import Processors

class TTWSServer:
    def __init__(self, host, port, db_pool=None, clients={}, send_event=None):
        self.host = host
        self.port = port
        self.proto = Proto()
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event)
        self.logger = logging.getLogger(__name__)

    async def handle_client(self, websocket):
        deviceType = None
        deviceName = None

        async for message in websocket:
            # Распаковываем пакет
            packet = self.proto.unpack_packet(message)

            if not packet:
                self.logger.warning("Невалидный пакет от ws клиента")
                continue

            # Валидируем структуру пакета
            try:
                MessageModel.model_validate(packet)
            except ValidationError as e:
                self.logger.warning(f"Ошибка валидации пакета: {e}")
                continue

            # Извлекаем данные из пакета
            seq = packet['seq']
            opcode = packet['opcode']
            payload = packet['payload']

            match opcode:
                case self.proto.SESSION_INIT:
                    # ПРИВЕТ АНДРЕЙ МАЛАХОВ
                    # не не удаляй этот коммент. пусть останется на релизе аххахаха
                    deviceType, deviceName = await self.processors.process_hello(payload, seq, websocket)
                case self.proto.PING:
                    await self.processors.process_ping(payload, seq, websocket)
                case self.proto.LOG:
                    # телеметрия аааа слежка цру фсб фбр
                    # УДАЛЯЕМ MYTRACKER ИЗ TAMTAM ТАМ ВИРУС
                    # майтрекер отправляет все ваши сообщения на сервер барака обамы. немедленно удаляем!!!
                    await self.processors.process_telemetry(payload, seq, websocket)
                # case self.proto.AUTH_REQUEST:
                #     await self.processors.process_auth_request(payload, seq, websocket)
                # case self.proto.VERIFY_CODE:
                #     await self.processors.process_verify_code(payload, seq, websocket)
                # case self.proto.FINAL_AUTH:
                #     await self.processors.process_final_auth(payload, seq, websocket, deviceType, deviceName)

                # лан я пойду. пока
                # а ок

    async def start(self):
        self.logger.info(f"Вебсокет запущен на порту {self.port}")

        async with serve(
            self.handle_client, self.host, self.port,
            max_size=65536,
            open_timeout=10,
            close_timeout=10,
        ):
            await asyncio.Future()