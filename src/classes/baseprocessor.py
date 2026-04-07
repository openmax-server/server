import logging
from common.config import ServerConfig
from common.static import Static
from common.tools import Tools
from common.proto_tcp import MobileProto
from common.proto_web import WebProto
from common.opcodes import Opcodes

class BaseProcessor:
    def __init__(self, db_pool=None, clients=None, send_event=None, type="socket"):
        if clients is None:
            clients = {}
        self.config = ServerConfig()
        self.static = Static()
        self.tools = Tools()
        self.opcodes = Opcodes()
        self.error_types = self.static.ErrorTypes()

        self.db_pool = db_pool
        self.clients = clients
        self.event = send_event
        self.logger = logging.getLogger(__name__)

        self.type = type

        if type == "socket":
            self.proto = MobileProto()
        elif type == "web":
            self.proto = WebProto()

    async def _send(self, writer, packet):
        try:
            # Если объектом является вебсокет, то используем функцию send для отправки
            if hasattr(writer, 'send'):
                await writer.send(packet)
            else: # В ином случае отправляем как в обычный сокет
                writer.write(packet)
                await writer.drain()
        except Exception:
            pass

    async def _send_error(self, seq, opcode, error_type, writer):
        payload = self.static.ERROR_TYPES.get(error_type, {
            "localizedMessage": "Неизвестная ошибка",
            "error": "unknown.error",
            "message": "Unknown error",
            "title": "Неизвестная ошибка"
        })

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_ERR, seq=seq, opcode=opcode, payload=payload
        )
        await self._send(writer, packet)