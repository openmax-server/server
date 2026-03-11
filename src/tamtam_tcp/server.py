import asyncio, logging, traceback
from tamtam_tcp.proto import Proto
from tamtam_tcp.processors import Processors
from common.rate_limiter import RateLimiter

class TTMobileServer:
    def __init__(self, host="0.0.0.0", port=443, ssl_context=None, db_pool=None, clients={}, send_event=None):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.clients = clients

        self.proto = Proto()
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event)

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
                    case self.proto.HELLO:
                        deviceType, deviceName = await self.processors.process_hello(payload, seq, writer)
                    case self.proto.REQUEST_CODE:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.proto.REQUEST_CODE, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.process_request_code(payload, seq, writer)
                    case self.proto.VERIFY_CODE:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.proto.VERIFY_CODE, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.process_verify_code(payload, seq, writer)
                    case self.proto.FINAL_AUTH:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.proto.FINAL_AUTH, self.processors.error_types.RATE_LIMITED, writer)
                        else:
                            await self.processors.process_final_auth(payload, seq, writer, deviceType, deviceName)
                    case _:
                        self.logger.warning(f"Неизвестный опкод {opcode}")
        except Exception as e:
            self.logger.error(f"Произошла ошибка при работе с клиентом {address[0]}:{address[1]}: {e}")
            traceback.print_exc()

        writer.close()
        self.logger.info(f"Прекратил работать работать с клиентом {address[0]}:{address[1]}")

    async def start(self):
        """Функция для запуска сервера"""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port, ssl=self.ssl_context
        )

        self.logger.info(f"Сокет запущен на порту {self.port}")

        async with self.server:
            await self.server.serve_forever()