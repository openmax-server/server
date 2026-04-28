import asyncio
from oneme.socket import OnemeMobile
from oneme.websocket import OnemeWS
from common.proto_tcp import MobileProto
from common.proto_web import WebProto
from classes.controllerbase import ControllerBase
from common.config import ServerConfig
from common.opcodes import Opcodes

class OnemeController(ControllerBase):
    def __init__(self):
        self.config = ServerConfig()
        self.proto = MobileProto()
        self.opcodes = Opcodes()

    async def event(self, target, client, eventData):
        # Извлекаем тип события и врайтер
        eventType = eventData.get("eventType")
        writer = client.get("writer")

        # Не отправляем событие самому себе
        if writer == eventData.get("writer"):
            return

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
                cmd=0, seq=1, opcode=self.opcodes.NOTIF_MESSAGE, payload=payload
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
                cmd=0, seq=1, opcode=self.opcodes.NOTIF_TYPING, payload=payload
            )
        elif eventType == "profile_updated":
            # Данные события
            profile = eventData.get("profile")

            # Данные пакета
            payload = {
                "profile": profile
            }

            # Создаем пакет
            packet = self.proto.pack_packet(
                cmd=0, seq=1, opcode=self.opcodes.NOTIF_PROFILE, payload=payload
            )
        elif eventType == "presence":
            userId = eventData.get("userId")
            presence = eventData.get("presence")
            event_time = eventData.get("time")

            payload = {
                "userId": userId,
                "presence": presence,
                "time": event_time
            }

            packet = self.proto.pack_packet(
                cmd=0, seq=1, opcode=self.opcodes.NOTIF_PRESENCE, payload=payload
            )

        # Отправляем пакет
        writer.write(packet)
        await writer.drain()

    def launch(self, api):
        async def _start_all():
            await asyncio.gather(
                OnemeMobile(
                    host=self.config.host,
                    port=self.config.oneme_tcp_port,
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event'],
                    telegram_bot=api.get('telegram_bot'),
                ).start(),
                OnemeWS(
                    host=self.config.host,
                    port=self.config.oneme_ws_port,
                    clients=api['clients'],
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    send_event=api['event']
                ).start()
            )

        return _start_all()