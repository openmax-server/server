import logging
import traceback
import websockets
from common.proto_web import WebProto
from tamtam.processors import Processors
from common.rate_limiter import RateLimiter
from common.opcodes import Opcodes
from common.tools import Tools

class TamTamWS:
    def __init__(self, host, port, clients, ssl_context, db_pool, send_event):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.clients = clients

        self.opcodes = Opcodes()

        self.proto = WebProto()
        self.processors = Processors(db_pool=db_pool, clients=clients, send_event=send_event, type="web")
        self.auth_required = Tools().auth_required

        # rate limiter
        self.auth_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60)

        self.read_timeout = 300  # Таймаут чтения из websocket (секунды)
        self.max_read_size = 65536  # Максимальный размер данных

    async def handle_client(self, websocket, path):
        """Функция для обработки WebSocket подключений"""
        # IP-адрес клиента
        address = websocket.remote_address
        self.logger.info(f"Работаю с клиентом {address[0]}:{address[1]}")

        deviceType = None
        deviceName = None

        userPhone = None
        userId = None
        hashedToken = None

        try:
            async for message in websocket:
                # Проверяем размер данных
                if len(message) > self.max_read_size:
                    self.logger.warning(f"Пакет от {address[0]}:{address[1]} превышает лимит ({len(message)} байт)")
                    break

                # Распаковываем данные
                packet = self.proto.unpack_packet(message)

                # Если пакет невалидный — пропускаем
                if not packet:
                    self.logger.warning(f"Невалидный пакет от {address[0]}:{address[1]}")
                    continue

                opcode = packet.get("opcode")
                seq = packet.get("seq")
                payload = packet.get("payload")

                match opcode:
                    case self.opcodes.SESSION_INIT:
                        deviceType, deviceName = await self.processors.session_init(payload, seq, websocket)
                    case self.opcodes.PING:
                        await self.processors.ping(payload, seq, websocket)
                    case self.opcodes.LOG:
                        await self.processors.log(payload, seq, websocket)
                    case self.opcodes.AUTH_REQUEST:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH_REQUEST, self.processors.error_types.RATE_LIMITED, websocket)
                        else:
                            await self.processors.auth_request(payload, seq, websocket)
                    case self.opcodes.AUTH:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH, self.processors.error_types.RATE_LIMITED, websocket)
                        else:
                            await self.processors.auth(payload, seq, websocket)
                    case self.opcodes.AUTH_CONFIRM:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.AUTH_CONFIRM, self.processors.error_types.RATE_LIMITED, websocket)
                        else:
                            await self.processors.auth_confirm(payload, seq, websocket, deviceType, deviceName)
                    case self.opcodes.LOGIN:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(seq, self.opcodes.LOGIN, self.processors.error_types.RATE_LIMITED, websocket)
                        else:
                            userPhone, userId, hashedToken = await self.processors.login(payload, seq, websocket)

                            if userPhone:
                                await self._finish_auth(websocket, address, userPhone, userId)
                    case self.opcodes.CONTACT_INFO:
                        await self.auth_required(
                            userPhone, self.processors.contact_info, payload, seq, websocket
                        )
                    case self.opcodes.CHAT_HISTORY:
                        await self.auth_required(
                            userPhone, self.processors.chat_history, payload, seq, websocket, userId
                        )
                    case _:
                        self.logger.warning(f"Неизвестный опкод {opcode}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Прекратил работать с клиентом {address[0]}:{address[1]}")
        except Exception as e:
            self.logger.error(f" Произошла ошибка при работе с клиентом {address[0]}:{address[1]}: {e}")
            traceback.print_exc()

        # Удаляем клиента из словаря при отключении
        if userId:
            await self._end_session(userId, address[0], address[1])
        
        self.logger.info(f"Прекратил работать с клиентом {address[0]}:{address[1]}")

    async def _finish_auth(self, websocket, addr, phone, id):
        """Завершение открытия сессии"""
        # Ищем пользователя в словаре
        user = self.clients.get(id)

        # Добавляем новое подключение в словарь
        if user:
            user["clients"].append(
                {
                    "writer": websocket,
                    "ip": addr[0],
                    "port": addr[1],
                    "protocol": "tamtam"
                }
            )
        else:
            self.clients[id] = {
                "phone": phone,
                "id": id,
                "clients": [
                    {
                        "writer": websocket,
                        "ip": addr[0],
                        "port": addr[1],
                        "protocol": "tamtam"
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
        """Функция для запуска WebSocket сервера"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context
        )

        self.logger.info(f"TT WebSocket запущен на порту {self.port}")

        await self.server.wait_closed()