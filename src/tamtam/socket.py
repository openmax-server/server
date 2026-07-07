import asyncio
import logging
import traceback
from common.proto_tcp import MobileProto
from tamtam.processors import Processors
from common.rate_limiter import RateLimiter
from common.opcodes import Opcodes
from common.tools import Tools

class TamTamMobile:
    def __init__(self, host, port, ssl_context, db_pool, clients, send_event):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.clients = clients

        self.opcodes = Opcodes()

        self.proto = MobileProto()
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event)
        self.auth_required = Tools().auth_required

        # rate limiter
        self.auth_rate_limiter = RateLimiter(max_attempts=15, window_seconds=60)

        self.read_timeout = 300 # Таймаут чтения из сокета (секунды)
        self.max_read_size = 65536 # Максимальный размер данных из сокета

    async def handle_client(self, reader, writer):
        """Функция для обработки подключений"""
        # IP-адрес клиента
        address = writer.get_extra_info("peername")
        self.logger.info(f"Работаю с клиентом {address[0]}:{address[1]}")

        deviceType = None
        deviceName = None

        userPhone = None
        userId = None
        hashedToken = None

        try:
            while True:
                # Читаем новые данные из сокета (с таймаутом!)
                try:
                    data = await asyncio.wait_for(
                        reader.read(self.max_read_size),
                        timeout=self.read_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.info(f"Таймаут соединения для {address[0]}:{address[1]}")
                    break

                # Если сокет закрыт - выходим из цикла
                if not data:
                    break

                # Проверяем размер данных
                if len(data) > self.max_read_size:
                    self.logger.warning(f"Пакет от {address[0]}:{address[1]} превышает лимит ({len(data)} байт)")
                    break

                # Распаковываем данные
                packet = self.proto.unpack_packet(data)

                # Если пакет невалидный — пропускаем
                if packet is None:
                    self.logger.warning(f"Невалидный пакет от {address[0]}:{address[1]}")
                    continue

                opcode = packet.get("opcode")
                seq = packet.get("seq")
                payload = packet.get("payload")

                match opcode:
                    case self.opcodes.SESSION_INIT:
                        deviceType, deviceName = await self.processors.session_init(payload, seq, writer)
                    case self.opcodes.PING:
                        await self.processors.ping(payload, seq, writer)
                    case self.opcodes.LOG:
                        await self.processors.log(payload, seq, writer)
                    case self.opcodes.AUTH_REQUEST:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH_REQUEST, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.auth_request(payload, seq, writer)
                    case self.opcodes.AUTH:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.auth(payload, seq, writer)
                    case self.opcodes.AUTH_CONFIRM:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH_CONFIRM, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.auth_confirm(payload, seq, writer, deviceType, deviceName, address[0])
                    case self.opcodes.LOGIN:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.LOGIN, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            userPhone, userId, hashedToken = await self.processors.login(payload, seq, writer)

                            if userPhone:
                                await self._finish_auth(writer, address, userPhone, userId)
                    case self.opcodes.LOGOUT:
                        await self.processors.logout(
                            seq, writer, hashedToken=hashedToken
                        )
                        break
                    case self.opcodes.CONTACT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.contact_info, payload, seq, writer
                        )
                    case self.opcodes.CHAT_HISTORY:
                        await self.auth_required(
                            userPhone, self.processors.chat_history, payload, seq, writer, userId
                        )
                    case self.opcodes.ASSETS_UPDATE:
                        await self.auth_required(
                            userPhone, self.processors.assets_update, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_GET:
                        await self.auth_required(
                            userPhone, self.processors.assets_get, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_GET_BY_IDS:
                        await self.auth_required(
                            userPhone, self.processors.assets_get_by_ids, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_ADD:
                        await self.auth_required(
                            userPhone, self.processors.assets_add, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_REMOVE:
                        await self.auth_required(
                            userPhone, self.processors.assets_remove, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_MOVE:
                        await self.auth_required(
                            userPhone, self.processors.assets_move, payload, seq, writer
                        )
                    case self.opcodes.ASSETS_LIST_MODIFY:
                        await self.auth_required(
                            userPhone, self.processors.assets_list_modify, payload, seq, writer
                        )
                    case self.opcodes.VIDEO_CHAT_HISTORY:
                        await self.auth_required(
                            userPhone, self.processors.video_chat_history, payload, seq, writer
                        )
                    case self.opcodes.MSG_SEND:
                        await self.auth_required(
                            userPhone, self.processors.msg_send, payload, seq, writer, userId, self.db_pool
                        )
                    case self.opcodes.MSG_TYPING:
                        await self.auth_required(
                            userPhone, self.processors.msg_typing, payload, seq, writer, userId
                        )
                    case self.opcodes.FOLDERS_GET:
                        await self.auth_required(
                            userPhone, self.processors.folders_get, payload, seq, writer, userPhone
                        )
                    case self.opcodes.FOLDERS_UPDATE:
                        await self.auth_required(
                            userPhone, self.processors.folders_update, payload, seq, writer, userPhone
                        )
                    case self.opcodes.SESSIONS_INFO:
                        await self.auth_required(
                            userPhone, self.processors.sessions_info, payload, seq, writer, userPhone, hashedToken
                        )
                    case self.opcodes.CHAT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.chat_info, payload, seq, writer, userId
                        )
                    case self.opcodes.CONTACT_LIST:
                        await self.auth_required(
                            userPhone, self.processors.contact_list, payload, seq, writer, userId
                        )
                    case self.opcodes.PROFILE:
                        await self.processors.profile(
                            payload, seq, writer, userId=userId
                        )
                    case self.opcodes.CHAT_SUBSCRIBE:
                        await self.auth_required(
                            userPhone, self.processors.chat_subscribe, payload, seq, writer
                        )
                    case self.opcodes.CONFIG:
                        await self.auth_required(
                            userPhone, self.processors.update_config, payload, seq, writer, userPhone, hashedToken
                        )
                    case self.opcodes.CONTACT_UPDATE:
                        await self.auth_required(
                            userPhone, self.processors.contact_update, payload, seq, writer, userId
                        )
                    case self.opcodes.CONTACT_PRESENCE:
                        await self.auth_required(
                            userPhone, self.processors.contact_presence, payload, seq, writer
                        )
                    case _:
                        self.logger.warning(f"Неизвестный опкод {opcode}")
        except Exception as e:
            self.logger.error(f"Произошла ошибка при работе с клиентом {address[0]}:{address[1]}: {e}")
            traceback.print_exc()

        # Удаляем клиента из словаря при отключении
        if userId:
            await self._end_session(userId, address[0], address[1])

        writer.close()
        self.logger.info(f"Прекратил работать с клиентом {address[0]}:{address[1]}")

    async def _finish_auth(self, writer, addr, phone, id):
        """Завершение открытия сессии"""
        # Ищем пользователя в словаре
        user = self.clients.get(id)

        # Добавляем новое подключение в словарь
        if user:
            user["clients"].append(
                {
                    "writer": writer,
                    "ip": addr[0],
                    "port": addr[1],
                    "protocol": "tamtam",
                    "type": "tcp"
                }
            )
        else:
            self.clients[id] = {
                "phone": phone,
                "id": id,
                "clients": [
                    {
                        "writer": writer,
                        "ip": addr[0],
                        "port": addr[1],
                        "protocol": "tamtam",
                        "type": "tcp"
                    }
                ]
            }

    async def _end_session(self, id, ip, port):
        """Завершение сессии"""
        # Получаем пользователя в списке
        user = self.clients.get(id)
        if not user:
            return

        # Получаем подключения пользователя
        clients = user.get("clients", [])

        # Удаляем нужное подключение из словаря
        for i, client in enumerate(clients):
            if (client.get("ip"), client.get("port")) == (ip, port):
                clients.pop(i)

    async def start(self):
        """Функция для запуска сервера"""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port, ssl=self.ssl_context
        )

        self.logger.info(f"Сокет запущен на порту {self.port}")

        try:
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            self.server.close()
            await self.server.wait_closed()