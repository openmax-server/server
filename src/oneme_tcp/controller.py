import asyncio
from oneme_tcp.server import OnemeMobileServer
from oneme_tcp.proto import Proto
from classes.controllerbase import ControllerBase
from common.config import ServerConfig

class OnemeMobileController(ControllerBase):
    def __init__(self):
        self.config = ServerConfig()
        self.proto = Proto()

    async def event(self, target, client, eventData):
        # Извлекаем тип события и врайтер
        eventType = eventData.get("eventType")
        writer = client.get("writer")

        # Обрабатываем событие
        if eventType == "new_msg":
            # Данные сообщения
            chatId = eventData.get("chatId")
            message = eventData.get("message")
            prevMessageId = eventData.get("prevMessageId")
            time = eventData.get("time")

            # Данные пакета
            payload = {
                "chatId": chatId,
                "message": message,
                "prevMessageId": prevMessageId,
                "ttl": False,
                "unread": 0,
                "mark": time
            }

            # Создаем пакет
            packet = self.proto.pack_packet(
                cmd=0, seq=1, opcode=self.proto.NOTIF_MESSAGE, payload=payload
            )
        elif eventType == "typing":
            # Данные события
            chatId = eventData.get("chatId")
            userId = eventData.get("userId")
            type = eventData.get("type")

            # Данные пакета
            payload = {
                "chatId": chatId,
                "userId": userId,
                "type": type
            }

            # Создаем пакет
            packet = self.proto.pack_packet(
                cmd=0, seq=1, opcode=self.proto.NOTIF_TYPING, payload=payload
            )

        # Отправляем пакет
        writer.write(packet)
        await writer.drain()

    def launch(self, api):
        async def _start_all():
            await asyncio.gather(
                OnemeMobileServer(
                    host=self.config.host,
                    port=self.config.oneme_tcp_port,
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event'],
                    telegram_bot=api.get('telegram_bot'),
                ).start()
            )

        return _start_all()