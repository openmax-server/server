import asyncio, logging, json
from websockets.asyncio.server import serve
from tamtam_ws.models import *
from pydantic import ValidationError
from tamtam_ws.proto import Proto
from tamtam_ws.processors import Processors

class TTWSServer:
    def __init__(self, host, port, db_pool=None, clients={}, send_event=None, origins=None):
        self.host = host
        self.port = port
        self.proto = Proto()
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event)
        self.logger = logging.getLogger(__name__)
        self.origins = origins

    async def handle_client(self, websocket):
        deviceType = None
        deviceName = None

        async for message in websocket:
            # Распаковываем пакет
            packet = self.proto.unpack_packet(message)

            # Если ничего не извлекли
            if packet is None:
                self.logger.error(f"Не удалось распаковать пакет - {message}")
                return

            # Валидируем структуру пакета
            try:
                MessageModel.model_validate(packet)
            except ValidationError as error:
                self.logger.error(f"Произошла ошибка при валидации структуры пакета: {error}")
                return
                
            # Извлекаем данные из пакета
            seq = packet['seq']
            opcode = packet['opcode']
            payload = packet['payload']

            match opcode:
                case self.proto.SESSION_INIT:
                    # ПРИВЕТ АНДРЕЙ МАЛАХОВ
                    # не не удаляй этот коммент. пусть останется на релизе аххахаха
                    deviceType, deviceType = await self.processors.process_hello(payload, seq, websocket)
                case self.proto.PING:
                    await self.processors.process_ping(payload, seq, websocket)
                case self.proto.LOG:
                    # телеметрия аааа слежка цру фсб фбр
                    # УДАЛЯЕМ MYTRACKER ИЗ TAMTAM ТАМ ВИРУС
                    # майтрекер отправляет все ваши сообщения на сервер барака обамы. немедленно удаляем!!!
                    await self.processors.process_telemetry(payload, seq, websocket)

                # лан я пойду. пока
                # а ок

    async def start(self):
        self.logger.info(f"Вебсокет запущен на порту {self.port}")

        async with serve(handler=self.handle_client, 
                         host=self.host, 
                         port=self.port,
                         origins=self.origins):
            await asyncio.Future()