import logging
import time
import traceback
import websockets
from common.proto_web import WebProto
from oneme.processors import Processors
from common.rate_limiter import RateLimiter
from common.opcodes import Opcodes
from common.tools import Tools

class OnemeWS:
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

    async def handle_client(self, websocket):
        """Функция для обработки WebSocket подключений"""
        # IP-адрес клиента
        address = websocket.remote_address
        self.logger.info(f"Работаю с клиентом {address[0]}:{address[1]}")

        deviceType = None
        deviceName = None
        appVersion = None

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
                        deviceType, deviceName, appVersion = await self.processors.session_init(
                            payload, seq, websocket
                        )
                    case self.opcodes.AUTH_REQUEST:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(
                                seq,
                                self.opcodes.AUTH_REQUEST,
                                self.processors.error_types.RATE_LIMITED,
                                websocket,
                            )
                        else:
                            await self.processors.auth_request(payload, seq, websocket)
                    case self.opcodes.AUTH:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(
                                seq,
                                self.opcodes.AUTH,
                                self.processors.error_types.RATE_LIMITED,
                                websocket,
                            )
                        else:
                            await self.processors.auth(
                                payload, seq, websocket, deviceType, deviceName, appVersion
                            )
                    case self.opcodes.AUTH_CONFIRM:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(
                                seq,
                                self.opcodes.AUTH_CONFIRM,
                                self.processors.error_types.RATE_LIMITED,
                                websocket,
                            )
                        elif payload and payload.get("tokenType") == "REGISTER":
                            await self.processors.auth_confirm(
                                payload, seq, websocket, deviceType, deviceName, appVersion
                            )
                        else:
                            self.logger.warning(
                                f"AUTH_CONFIRM с неизвестным tokenType: {payload}"
                            )
                    case self.opcodes.LOGIN:
                        if not self.auth_rate_limiter.is_allowed(address[0]):
                            await self.processors._send_error(
                                seq,
                                self.opcodes.LOGIN,
                                self.processors.error_types.RATE_LIMITED,
                                websocket,
                            )
                        else:
                            (
                                userPhone,
                                userId,
                                hashedToken,
                            ) = await self.processors.login(payload, seq, websocket, deviceType, appVersion)

                            if userPhone:
                                await self._finish_auth(
                                    websocket, address, userPhone, userId
                                )
                    case self.opcodes.LOGOUT:
                        await self.processors.logout(
                            seq, websocket, hashedToken=hashedToken
                        )
                        break
                    case self.opcodes.PING:
                        await self.processors.ping(payload, seq, websocket, userId)
                    case self.opcodes.LOG:
                        await self.processors.log(payload, seq, websocket)
                    case self.opcodes.ASSETS_UPDATE:
                        await self.auth_required(
                            userPhone,
                            self.processors.assets_update,
                            payload,
                            seq,
                            websocket,
                        )
                    case self.opcodes.VIDEO_CHAT_HISTORY:
                        await self.auth_required(
                            userPhone,
                            self.processors.video_chat_history,
                            payload,
                            seq,
                            websocket,
                        )
                    case self.opcodes.MSG_SEND:
                        await self.auth_required(
                            userPhone,
                            self.processors.msg_send,
                            payload,
                            seq,
                            websocket,
                            userId,
                            self.db_pool,
                        )
                    case self.opcodes.FOLDERS_GET:
                        await self.auth_required(
                            userPhone,
                            self.processors.folders_get,
                            payload,
                            seq,
                            websocket,
                            userPhone,
                        )
                    case self.opcodes.FOLDERS_UPDATE:
                        await self.auth_required(
                            userPhone,
                            self.processors.folders_update,
                            payload,
                            seq,
                            websocket,
                            userPhone,
                        )
                    case self.opcodes.SESSIONS_INFO:
                        await self.auth_required(
                            userPhone,
                            self.processors.sessions_info,
                            payload,
                            seq,
                            websocket,
                            userPhone,
                            hashedToken,
                        )
                    case self.opcodes.CHAT_INFO:
                        await self.auth_required(
                            userPhone,
                            self.processors.chat_info,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.CHAT_HISTORY:
                        await self.auth_required(
                            userPhone,
                            self.processors.chat_history,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.CONTACT_INFO_BY_PHONE:
                        await self.auth_required(
                            userPhone,
                            self.processors.contact_info_by_phone,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.OK_TOKEN:
                        await self.auth_required(
                            userPhone, self.processors.ok_token, payload, seq, websocket
                        )
                    case self.opcodes.MSG_TYPING:
                        await self.auth_required(
                            userPhone,
                            self.processors.msg_typing,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.CONTACT_INFO:
                        await self.auth_required(
                            userPhone,
                            self.processors.contact_info,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.CONTACT_LIST:
                        await self.auth_required(
                            userPhone,
                            self.processors.contact_list,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.COMPLAIN_REASONS_GET:
                        await self.auth_required(
                            userPhone,
                            self.processors.complain_reasons_get,
                            payload,
                            seq,
                            websocket,
                        )
                    case self.opcodes.PROFILE:
                        await self.processors.profile(
                            payload, seq, websocket, userId=userId
                        )
                    case self.opcodes.CHAT_SUBSCRIBE:
                        await self.auth_required(
                            userPhone,
                            self.processors.chat_subscribe,
                            payload,
                            seq,
                            websocket,
                        )
                    case self.opcodes.CONFIG:
                        await self.auth_required(
                            userPhone,
                            self.processors.update_config,
                            payload,
                            seq,
                            websocket,
                            userPhone,
                            hashedToken,
                        )
                    case self.opcodes.CONTACT_UPDATE:
                        await self.auth_required(
                            userPhone,
                            self.processors.contact_update,
                            payload,
                            seq,
                            websocket,
                            userId,
                        )
                    case self.opcodes.CONTACT_PRESENCE:
                        await self.auth_required(
                            userPhone,
                            self.processors.contact_presence,
                            payload,
                            seq,
                            websocket
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
                    "protocol": "oneme"
                }
            )
        else:
            self.clients[id] = {
                "phone": phone,
                "id": id,
                "status": 2,
                "last_seen": 0,
                "clients": [
                    {
                        "writer": websocket,
                        "ip": addr[0],
                        "port": addr[1],
                        "protocol": "oneme"
                    }
                ]
            }

        await self._broadcast_presence(id, True)

    async def _broadcast_presence(self, userId, online):
        now = int(time.time())
        now_ms = int(time.time() * 1000)

        if online:
            presence_data = {"on": "ON", "seen": now, "status": 1}
        else:
            presence_data = {"seen": now}

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT owner_id FROM contacts WHERE contact_id = %s",
                    (userId,)
                )
                contact_owners = await cursor.fetchall()

        for row in contact_owners:
            owner_id = int(row.get("owner_id"))
            if owner_id in self.clients:
                await self.processors.event(
                    owner_id,
                    {
                        "eventType": "presence",
                        "userId": userId,
                        "presence": presence_data,
                        "time": now_ms,
                    }
                )

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

        if not clients:
            now = int(time.time())
            user["status"] = 0
            user["last_seen"] = now

            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE users SET lastseen = %s WHERE id = %s",
                        (str(now), id)
                    )

            await self._broadcast_presence(id, False)

    async def start(self):
        """Функция для запуска WebSocket сервера"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context
        )

        self.logger.info(f"WebSocket запущен на порту {self.port}")

        await self.server.wait_closed()