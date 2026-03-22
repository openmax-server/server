import asyncio, logging, traceback
from common.proto_tcp import MobileProto
from tamtam.processors import Processors
from common.rate_limiter import RateLimiter
from common.opcodes import Opcodes
from common.tools import Tools

class TTMobileServer:
    def __init__(self, host="0.0.0.0", port=443, ssl_context=None, db_pool=None, clients={}, send_event=None):
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
        self.auth_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60)

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
                            await self.processors.auth_confirm(payload, seq, writer, deviceType, deviceName)
                    case self.opcodes.LOGIN:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.LOGIN, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            userPhone, userId, hashedToken = await self.processors.login(payload, seq, writer)

                            if userPhone:
                                await self._finish_auth(writer, address, userPhone, userId)
                    case self.opcodes.CONTACT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.contact_info, payload, seq, writer
                        )
                    case _:
                        self.logger.warning(f"Неизвестный опкод {opcode}")
        except Exception as e:
            self.logger.error(f"Произошла ошибка при работе с клиентом {address[0]}:{address[1]}: {e}")
            traceback.print_exc()

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
                    "protocol": "tamtam_mobile"
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
                        "protocol": "tamtam_mobile"
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