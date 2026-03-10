import asyncio, logging, traceback
from oneme_tcp.proto import Proto
from oneme_tcp.processors import Processors
from common.tools import Tools

class OnemeMobileServer:
    def __init__(self, host="0.0.0.0", port=443, ssl_context=None, db_pool=None, clients={}, send_event=None, telegram_bot=None):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.clients = clients

        self.proto = Proto()
        self.auth_required = Tools().auth_required
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event, telegram_bot=telegram_bot)

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
                # Читаем новые данные из сокета
                data = await reader.read(4098)

                # Если сокет закрыт - выходим из цикла
                if not data:
                    break

                # Распаковываем данные
                packet = self.proto.unpack_packet(data)

                opcode = packet.get("opcode")
                seq = packet.get("seq")
                payload = packet.get("payload")

                match opcode:
                    case self.proto.SESSION_INIT:
                        deviceType, deviceName = await self.processors.process_hello(payload, seq, writer)
                    case self.proto.AUTH_REQUEST:
                        await self.processors.process_request_code(payload, seq, writer)
                    case self.proto.AUTH:
                        await self.processors.process_verify_code(payload, seq, writer, deviceType, deviceName)
                    case self.proto.LOGIN:
                        userPhone, userId, hashedToken = await self.processors.process_login(payload, seq, writer)
                    
                        # Если авторизация на сервере успешная - можем завершить авторизацию
                        if userPhone:
                            await self._finish_auth(writer, address, userPhone, userId)
                    case self.proto.LOGOUT:
                        await self.processors.process_logout(seq, writer, hashedToken=hashedToken)
                        break
                    case self.proto.PING:
                        await self.processors.process_ping(payload, seq, writer)
                    case self.proto.LOG:
                        await self.processors.process_telemetry(payload, seq, writer)
                    case self.proto.ASSETS_UPDATE:
                        await self.auth_required(
                            userPhone, self.processors.process_get_assets, payload, seq, writer
                        )
                    case self.proto.VIDEO_CHAT_HISTORY:
                        await self.auth_required(
                            userPhone, self.processors.process_get_call_history, payload, seq, writer
                        )
                    case self.proto.MSG_SEND:
                        await self.auth_required(
                            userPhone, self.processors.process_send_message, payload, seq, writer, senderId=userId, db_pool=self.db_pool
                        )
                    case self.proto.FOLDERS_GET:
                        await self.auth_required(
                            userPhone, self.processors.process_get_folders, payload, seq, writer, senderPhone=userPhone
                        )
                    case self.proto.SESSIONS_INFO:
                        await self.auth_required(
                            userPhone, self.processors.process_get_sessions, payload, seq, writer, senderPhone=userPhone, hashedToken=hashedToken
                        )
                    case self.proto.CHAT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.process_search_chats, payload, seq, writer, senderId=userId
                        )
                    case self.proto.CONTACT_INFO_BY_PHONE:
                        await self.auth_required(
                            userPhone, self.processors.process_search_by_phone, payload, seq, writer, senderId=userId
                        )
                    case self.proto.OK_TOKEN:
                        await self.auth_required(
                            userPhone, self.processors.process_get_call_token, payload, seq, writer
                        )
                    case self.proto.MSG_TYPING:
                        await self.auth_required(
                            userPhone, self.processors.process_typing, payload, seq, writer, senderId=userId
                        )
                    case self.proto.CONTACT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.process_search_users, payload, seq, writer
                        )
                    case self.proto.COMPLAIN_REASONS_GET:
                        await self.auth_required(
                            userPhone, self.processors.process_complain_reasons_get, payload, seq, writer
                        )
                    case _:
                        self.logger.warning(f"Неизвестный опкод {opcode}")
        except Exception as e:
            self.logger.error(f"Произошла ошибка при работе с клиентом {address[0]}:{address[1]}: {e}")
            traceback.print_exc()

        # Удаляем клиента из словаря
        if userPhone:
            await self._end_session(userId, address[0], address[1])

        writer.close()
        self.logger.info(f"Прекратил работать работать с клиентом {address[0]}:{address[1]}")

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
                    "protocol": "oneme_mobile"
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
                        "protocol": "oneme_mobile"
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

        async with self.server:
            await self.server.serve_forever()