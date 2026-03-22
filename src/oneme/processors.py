import json
import secrets
import hashlib
import time
import logging
from oneme.models import *
from common.proto_tcp import MobileProto
from common.proto_web import WebProto
from common.opcodes import Opcodes
from oneme.config import OnemeConfig
from common.tools import Tools
from common.config import ServerConfig
from common.static import Static
from common.sms import send_sms_code

class Processors:
    def __init__(self, db_pool=None, clients={}, send_event=None, telegram_bot=None, type="socket"):
        self.tools = Tools()
        self.config = ServerConfig()
        self.static = Static()
        self.opcodes = Opcodes()
        self.server_config = OnemeConfig().SERVER_CONFIG
        self.error_types = self.static.ErrorTypes()
        self.chat_types = self.static.ChatTypes()

        self.db_pool = db_pool
        self.event = send_event
        self.clients = clients
        self.telegram_bot = telegram_bot
        self.logger = logging.getLogger(__name__)

        if type == "socket":
            self.proto = MobileProto()
        elif type == "web":
            self.proto = WebProto()

    async def _send(self, writer, packet):
        try:
            writer.write(packet)
            await writer.drain()
        except Exception as error:
            self.logger.error(f"Ошибка при отправке пакета - {error}")

    async def _send_error(self, seq, opcode, type, writer):
        payload = self.static.ERROR_TYPES.get(type, {
            "localizedMessage": "Неизвестная ошибка",
            "error": "unknown.error",
            "message": "Unknown error",
            "title": "Неизвестная ошибка"
        })
        
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_ERR, seq=seq, opcode=opcode, payload=payload
        )
        
        await self._send(writer, packet)

    async def session_init(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.SESSION_INIT, self.error_types.INVALID_PAYLOAD, writer)
            return None, None

        # Получаем данные из пакета
        deviceType = payload.get("userAgent").get("deviceType")
        deviceName = payload.get("userAgent").get("deviceName")

        # Данные пакета
        payload = {
            "location": "RU",
            "app-update-type": 0, # 1 = принудительное обновление
            "reg-country-code": self.static.REG_COUNTRY_CODES,
            "phone-auto-complete-enabled": False,
            "lang": True
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSION_INIT, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return deviceType, deviceName
    
    async def ping(self, payload, seq, writer):
        """Обработчик пинга"""
        # Валидируем данные пакета
        try:
            PingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.PING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.PING, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def log(self, payload, seq, writer):
        """Обработчик телеметрии"""
        # TODO: можно было бы реализовать валидацию телеметрии, но сейчас это не особо важно

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOG, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def auth_request(self, payload, seq, writer):
        """Обработчик запроса кода"""
        try:
            RequestCodePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.AUTH_REQUEST, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем телефон из пакета
        phone = payload.get("phone").replace("+", "").replace(" ", "").replace("-", "")

        # Генерируем токен
        token = secrets.token_urlsafe(128)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Время истечения токена
        expires = int(time.time()) + 300

        user_exists = False

        # Ищем пользователя
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
                user = await cursor.fetchone()

        # Получаем код через SMS шлюз или генерируем локально (безопасность прежде всего)
        if self.config.sms_gateway_url:
            code = await send_sms_code(self.config.sms_gateway_url, phone)

            if code is None:
                code = str(secrets.randbelow(900000) + 100000)
        else:
            code = str(secrets.randbelow(900000) + 100000)

        # Хешируем
        code_hash = hashlib.sha256(code.encode()).hexdigest()

        # Сохраняем токен и если нужно отправляем код через тг
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if user:
                    user_exists = True
                    # Сохраняем токен
                    await cursor.execute(
                        "INSERT INTO auth_tokens (phone, token_hash, code_hash, expires) VALUES (%s, %s, %s, %s)",
                        (phone, token_hash, code_hash, expires,)
                    )

                    # Если тг бот включен, и тг привязан к аккаунту - отправляем туда сообщение
                    if not self.config.sms_gateway_url and self.telegram_bot and user.get("telegram_id"):
                        await self.telegram_bot.send_code(chat_id=int(user.get("telegram_id")), phone=phone, code=code)
                else:
                    # Пользователь не найден - сохраняем токен со state='register'
                    # чтобы после верификации кода направить на экран регистрации
                    await cursor.execute(
                        "INSERT INTO auth_tokens (phone, token_hash, code_hash, expires, state) VALUES (%s, %s, %s, %s, %s)",
                        (phone, token_hash, code_hash, expires, "register",)
                    )

        # Данные пакета
        payload = {
            "requestMaxDuration": 60000,
            "requestCountLeft": 10,
            "altActionDuration": 60000,
            "codeLength": 6,
            "token": token
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH_REQUEST, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        self.logger.debug(f"Код для {phone}: {code} (существующий={user_exists})")

    async def auth(self, payload, seq, writer, deviceType, deviceName):
        """Обработчик проверки кода"""
        try:
            VerifyCodePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.AUTH, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        code = payload.get("verifyCode")
        token = payload.get("token")

        # Хешируем токен с кодом
        hashed_code = hashlib.sha256(code.encode()).hexdigest()
        hashed_token = hashlib.sha256(token.encode()).hexdigest()

        # Генерируем постоянный токен
        login = secrets.token_urlsafe(128)
        hashed_login = hashlib.sha256(login.encode()).hexdigest()

        # Ищем токен с кодом
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Ищем токен
                await cursor.execute(
                    "SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP()",
                    (hashed_token,)
                )
                stored_token = await cursor.fetchone()

                # Если токен просрочен, или его нет - отправляем ошибку
                if stored_token is None:
                    await self._send_error(seq, self.opcodes.AUTH, self.error_types.CODE_EXPIRED, writer)
                    return

                # Проверяем код
                if stored_token.get("code_hash") != hashed_code:
                    await self._send_error(seq, self.opcodes.AUTH, self.error_types.INVALID_CODE, writer)
                    return

                # Если это новый пользователь - переводим токен в state='verified'
                # и отдаём клиенту REGISTER токен, чтобы он показал экран ввода имени
                if stored_token.get("state") == "register":
                    await cursor.execute(
                        "UPDATE auth_tokens SET state = %s WHERE token_hash = %s",
                        ("verified", hashed_token,)
                    )
                    packet = self.proto.pack_packet(
                        cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH,
                        payload={
                            "tokenAttrs": {
                                "REGISTER": {
                                    "token": token
                                }
                            },
                            "presetAvatars": []
                        }
                    )
                    await self._send(writer, packet)
                    return

                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Удаляем токен
                await cursor.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,))

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (stored_token.get("phone"), hashed_login, deviceType, deviceName, "Little Saint James Island", int(time.time()),)   # весь покрытый зеленью, абсолютно весь, остров невезения в океане есть
                )

        # Генерируем профиль
        # Аватарка с биографией
        photoId = None if not account.get("avatar_id") else int(account.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not account.get("description") else account.get("description")

        # Собираем данные пакета
        payload = {
            "tokenAttrs": {
                "LOGIN": {
                    "token": login
                }
            },
            "profile": self.tools.generate_profile(
                id=account.get("id"),
                phone=int(account.get("phone")),
                avatarUrl=avatar_url,
                photoId=photoId,
                updateTime=int(account.get("updatetime")),
                firstName=account.get("firstname"),
                lastName=account.get("lastname"),
                options=json.loads(account.get("options")),
                description=description,
                accountStatus=int(account.get("accountstatus")),
                profileOptions=json.loads(account.get("profileoptions")),
                includeProfileOptions=True,
                username=account.get("username")
            )
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def auth_confirm(self, payload, seq, writer, deviceType, deviceName):
        """Обработчик подтверждения регистрации нового пользователя"""
        # Валидируем данные пакета
        try:
            AuthConfirmRegisterPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.AUTH_CONFIRM, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        token = payload.get("token")
        first_name = payload.get("firstName").strip()
        last_name = (payload.get("lastName") or "").strip()

        # Хешируем токен
        hashed_token = hashlib.sha256(token.encode()).hexdigest()

        # Генерируем постоянный логин-токен
        login = secrets.token_urlsafe(128)
        hashed_login = hashlib.sha256(login.encode()).hexdigest()

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Ищем токен - он должен быть в state='verified'
                await cursor.execute(
                    "SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP() AND state = %s",
                    (hashed_token, "verified",)
                )
                stored_token = await cursor.fetchone()

                # Если токен не найден или просрочен - отправляем ошибку
                if stored_token is None:
                    await self._send_error(seq, self.opcodes.AUTH_CONFIRM, self.error_types.CODE_EXPIRED, writer)
                    return

                phone = stored_token.get("phone")

                # Проверяем что пользователь с таким телефоном ещё не существует
                await cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if await cursor.fetchone():
                    await self._send_error(seq, self.opcodes.AUTH_CONFIRM, self.error_types.INVALID_PAYLOAD, writer)
                    return

                now_ms = int(time.time() * 1000)
                now_s = int(time.time())

                # Создаем пользователя
                await cursor.execute(
                    """
                    INSERT INTO users
                        (id, phone, telegram_id, firstname, lastname, username,
                        profileoptions, options, accountstatus, updatetime, lastseen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        self.tools.generate_id(), phone, None, first_name, last_name, None,
                        json.dumps([]), json.dumps(["TT", "ONEME"]),
                        0, str(now_ms), str(now_s),
                    )
                )

                user_id = cursor.lastrowid

                # Добавляем данные аккаунта
                await cursor.execute(
                    """
                    INSERT INTO user_data
                        (phone, contacts, folders, user_config, chat_config)
                    VALUES (%s %s, %s, %s, %s)
                    """,
                    (
                        phone,
                        json.dumps([]),
                        json.dumps(self.static.USER_FOLDERS),
                        json.dumps(self.static.USER_SETTINGS),
                        json.dumps({}),
                    )
                )

                # Удаляем токен
                await cursor.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,))

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (phone, hashed_login, deviceType or "ANDROID", deviceName or "Unknown", "Little Saint James Island", now_s,)
                )

        # Генерируем профиль
        profile = self.tools.generate_profile(
            id=user_id,
            phone=int(phone),
            avatarUrl=None,
            photoId=None,
            updateTime=now_ms,
            firstName=first_name,
            lastName=last_name,
            options=["ONEME"],
            description=None,
            accountStatus=0,
            profileOptions=[],
            includeProfileOptions=True,
            username=None
        )

        # Собираем данные пакета
        payload = {
            "userToken": "0",
            "profile": profile,
            "tokenType": "LOGIN",
            "token": login
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH_CONFIRM, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        self.logger.info(f"Новый пользователь зарегистрирован: phone={phone} id={user_id} name={first_name} {last_name}")

    async def login(self, payload, seq, writer):
        """Обработчик авторизации клиента на сервере"""
        # Валидируем данные пакета
        try:
            LoginPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.LOGIN, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Чаты, где состоит пользователь
        chats = []

        # Получаем данные из пакета
        token = payload.get("token")

        # Хешируем токен
        hashed_token = hashlib.sha256(token.encode()).hexdigest()

        # Ищем токен в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM tokens WHERE token_hash = %s", (hashed_token,))
                token_data = await cursor.fetchone()

                # Если токен не найден, отправляем ошибку
                if token_data is None:
                    await self._send_error(seq, self.opcodes.LOGIN, self.error_types.INVALID_TOKEN, writer)
                    return

                # Ищем аккаунт пользователя в бд
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (token_data.get("phone"),))
                user = await cursor.fetchone()

                # Ищем данные пользователя в бд
                await cursor.execute("SELECT * FROM user_data WHERE phone = %s", (token_data.get("phone"),))
                user_data = await cursor.fetchone()

                # Ищем все чаты, где состоит пользователь
                await cursor.execute(
                    "SELECT * FROM chat_participants WHERE user_id = %s", 
                    (user.get('id'))
                )
                user_chats = await cursor.fetchall()

                for chat in user_chats:
                    chats.append(
                        chat.get("chat_id")
                    )

        # Аватарка с биографией
        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not user.get("description") else user.get("description")

        # Генерируем профиль
        profile = self.tools.generate_profile(
            id=user.get("id"),
            phone=int(user.get("phone")),
            avatarUrl=avatar_url,
            photoId=photoId,
            updateTime=int(user.get("updatetime")),
            firstName=user.get("firstname"),
            lastName=user.get("lastname"),
            options=json.loads(user.get("options")),
            description=description,
            accountStatus=int(user.get("accountstatus")),
            profileOptions=json.loads(user.get("profileoptions")),
            includeProfileOptions=True,
            username=user.get("username")
        )

        chats = await self.tools.generate_chats(
            chats, self.db_pool, user.get("id")
        )

        # Формируем данные пакета
        payload = {
            "profile": profile,
            "chats": chats,
            "chatMarker": 0,
            "messages": {},
            "contacts": [],
            "presence": {},
            "config": {
                "server": self.server_config,
                "user": json.loads(user_data.get("user_config"))
            },
            "token": token,
            "videoChatHistory": False,
            "time": int(time.time() * 1000)
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOGIN, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return int(user.get("phone")), int(user.get("id")), hashed_token

    async def logout(self, seq, writer, hashedToken):
        """Обработчик завершения сессии"""
        # Удаляем токен из бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM tokens WHERE token_hash = %s", (hashedToken,))
        
        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOGOUT, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def assets_update(self, payload, seq, writer):
        """Обработчик запроса ассетов клиента на сервере"""
        # Валидируем данные пакета
        try:
            AssetsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: сейчас это заглушка, а попозже нужно сделать полноценную реализацию

        # Данные пакета
        payload = {
            "sections": [],
            "sync": int(time.time() * 1000)
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_UPDATE, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def video_chat_history(self, payload, seq, writer):
        """Обработчик получения истории звонков"""
        # Валидируем данные пакета
        try:
            GetCallHistoryPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.VIDEO_CHAT_HISTORY, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: сейчас это заглушка, а попозже нужно сделать полноценную реализацию

        # Данные пакета
        payload = {
            "hasMore": False,
            "history": [],
            "backwardMarker": 0,
            "forwardMarker": 0
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.VIDEO_CHAT_HISTORY, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def msg_send(self, payload, seq, writer, senderId, db_pool):
        """Функция отправки сообщения"""
        # Валидируем данные пакета
        try:
            SendMessagePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Извлекаем данные из пакета
        userId = payload.get("userId")
        chatId = payload.get("chatId")
        message = payload.get("message")

        elements = message.get("elements") or []
        attaches = message.get("attaches") or []
        cid = message.get("cid") or 0
        text = message.get("text") or ""

        # Вычисляем ID чата по ID пользователя и ID отправителя, 
        # в случае отсутствия ID чата
        if not chatId:
            chatId = userId ^ senderId

        # Если клиент хочет отправить сообщение в избранное, 
        # то выставляем в качестве ID чата ID отправителя
        # (А ещё используем это, если клиент вообще ничего не указал)
        if chatId == 0 or not chatId:
            chatId = senderId
            participants = [senderId]
        else:
            # Если все таки клиент хочет отправить сообщение в нормальный чат,
            # то ищем его в базе данных (извлекать список участников все таки тоже надо)
            async with db_pool.acquire() as db_connection:
                async with db_connection.cursor() as cursor:
                    await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                    chat = await cursor.fetchone()

                    # Если нет такого чата - выбрасываем ошибку
                    if not chat:
                        await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.CHAT_NOT_FOUND, writer)
                        return
                    
                    # Список участников
                    participants = await self.tools.get_chat_participants(chatId, db_pool)

                    # Проверяем, является ли отправитель участником чата
                    if int(senderId) not in participants:
                        await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.CHAT_NOT_ACCESS, writer)
                        return

        # Добавляем сообщение в историю
        messageId, lastMessageId, messageTime = await self.tools.insert_message(
            chatId=chatId,
            senderId=senderId,
            text=text,
            attaches=attaches,
            elements=elements,
            cid=cid,
            type="USER",
            db_pool=self.db_pool
        )

        # Готовое тело сообщения
        bodyMessage = {
            "id": messageId,
            "time": messageTime,
            "type": "USER",
            "sender": senderId,
            "cid": cid,
            "text": text,
            "attaches": attaches,
            "elements": elements
        }

        # Отправляем событие всем участникам чата
        for participant in participants:
            await self.event(
                participant,
                {
                    "eventType": "new_msg",
                    "chatId": 0 if chatId == senderId else chatId,
                    "message": bodyMessage,
                    "prevMessageId": lastMessageId,
                    "time": messageTime,
                    "writer": writer
                }
            )

        # Данные пакета
        payload = {
            "chatId": 0 if chatId == senderId else chatId,
            "message": bodyMessage,
            "unread": 0,
            "mark": messageTime
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.MSG_SEND, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def folders_get(self, payload, seq, writer, senderPhone):
        """Синхронизация папок с сервером"""
        # Валидируем данные пакета
        try:
            SyncFoldersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.FOLDERS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Ищем папки в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT folders FROM user_data WHERE phone = %s", (int(senderPhone),))
                result_folders = await cursor.fetchone()
                user_folders = json.loads(result_folders.get("folders"))

        # Создаем данные пакета
        payload = {
            "folderSync": int(time.time() * 1000),
            "folders": self.static.ALL_CHAT_FOLDER + user_folders.get("folders"),
            "foldersOrder": self.static.ALL_CHAT_FOLDER_ORDER + user_folders.get("foldersOrder"),
            "allFilterExcludeFolders": user_folders.get("allFilterExcludeFolders")
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.FOLDERS_GET, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def sessions_info(self, payload, seq, writer, senderPhone, hashedToken):
        """Получение активных сессий на аккаунте"""
        # Готовый список сессий
        sessions = []

        # Ищем сессии в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM tokens WHERE phone = %s", (str(senderPhone),))
                user_sessions = await cursor.fetchall()

        # Собираем сессии в список
        for session in user_sessions:
            sessions.append(
                {
                    "time": int(session.get("time")),
                    "client": f"MAX {session.get('device_type')}",
                    "info": session.get("device_name"),
                    "location": session.get("location"),
                    "current": True if session.get("token_hash") == hashedToken else False
                }
            )

        # Создаем данные пакета
        payload = {
            "sessions": sessions
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSIONS_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def contact_info(self, payload, seq, writer):
        """Поиск пользователей по ID"""
        # Валидируем данные пакета
        try:
            SearchUsersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_INFO, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Итоговый список пользователей
        users = []

        # ID пользователей, которые нам предстоит найти
        contactIds = payload.get("contactIds")

        # Ищем пользователей в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for contactId in contactIds:
                    await cursor.execute("SELECT * FROM users WHERE id = %s", (contactId,))
                    user = await cursor.fetchone()

                    # Если такой пользователь есть, добавляем его в список
                    if user:
                        # Аватарка с биографией
                        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
                        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
                        description = None if not user.get("description") else user.get("description")

                        # Генерируем профиль
                        users.append(
                            self.tools.generate_profile(
                                id=user.get("id"),
                                phone=int(user.get("phone")),
                                avatarUrl=avatar_url,
                                photoId=photoId,
                                updateTime=int(user.get("updatetime")),
                                firstName=user.get("firstname"),
                                lastName=user.get("lastname"),
                                options=json.loads(user.get("options")),
                                description=description,
                                accountStatus=int(user.get("accountstatus")),
                                profileOptions=json.loads(user.get("profileoptions")),
                                includeProfileOptions=False,
                                username=user.get("username")
                            )
                        )

        # Создаем данные пакета
        payload = {
            "contacts": users
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def chat_info(self, payload, seq, writer, senderId):
        """Поиск чатов по ID"""
        # Валидируем данные пакета
        try:
            SearchChatsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CHAT_INFO, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Итоговый список чатов
        chats = []

        # ID чатов, которые нам предстоит найти
        chatIds = payload.get("chatIds")

        # Ищем чаты в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for chatId in chatIds:
                    if chatId != 0:
                        await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                        chat = await cursor.fetchone()
                        
                        if chat:
                            # Проверяем, является ли пользователь участником чата
                            participants = await self.tools.get_chat_participants(chatId, self.db_pool)
                            # (в max нельзя смотреть и отправлять сообщения в чат, в котором ты не участник, в отличие от tg (например, комментарии в каналах),
                            # так что надо тоже так делать)
                            if int(senderId) not in participants:
                                continue

                            # Получаем последнее сообщение из чата
                            message, messageTime = await self.tools.get_last_message(
                                chatId, self.db_pool
                            )

                            # Добавляем чат в список
                            chats.append(
                                self.tools.generate_chat(
                                    chatId, chat.get("owner"),
                                    chat.get("type"), participants,
                                    message, messageTime
                                )
                            )
                    else:
                        # Получаем последнее сообщение из чата
                        message, messageTime = await self.tools.get_last_message(
                            senderId, self.db_pool
                        )

                        # ID избранного
                        chatId = senderId ^ senderId

                        # Добавляем чат в список
                        chats.append(
                            self.tools.generate_chat(
                                chatId, senderId, 
                                "DIALOG", [senderId],
                                message, messageTime
                            )
                        )

        # Создаем данные пакета
        payload = {
            "chats": chats
        }

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def contact_info_by_phone(self, payload, seq, writer, senderId):
        """Поиск по номеру телефона"""
        # Валидируем данные пакета
        try:
            SearchByPhonePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_INFO_BY_PHONE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Ищем пользователя в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (int(payload.get("phone")),))
                user = await cursor.fetchone()

                # Если пользователь не найден, отправляем ошибку
                if not user:
                    await self._send_error(seq, self.opcodes.CONTACT_INFO_BY_PHONE, self.error_types.USER_NOT_FOUND, writer)
                    return
                
                # ID чата
                chatId = senderId ^ user.get("id")

                # Ищем диалог в бд
                await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                chat = await cursor.fetchone()

                # Если диалога нет - создаем
                if not chat:
                    await cursor.execute(
                        "INSERT INTO chats (id, owner, type) VALUES (%s, %s, %s)",
                        (chatId, senderId, "DIALOG")
                    )

                    # Добавляем участников в таблицу chat_participants
                    participants = [int(senderId), int(user.get("id"))]
                    
                    for user_id in participants:
                        await cursor.execute(
                            "INSERT INTO chat_participants (chat_id, user_id) VALUES (%s, %s)",
                            (chatId, user_id)
                        )

        # Аватарка с биографией
        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not user.get("description") else user.get("description")

        # Генерируем профиль
        profile = self.tools.generate_profile(
            id=user.get("id"),
            phone=int(user.get("phone")),
            avatarUrl=avatar_url,
            photoId=photoId,
            updateTime=int(user.get("updatetime")),
            firstName=user.get("firstname"),
            lastName=user.get("lastname"),
            options=json.loads(user.get("options")),
            description=description,
            accountStatus=int(user.get("accountstatus")),
            profileOptions=json.loads(user.get("profileoptions")),
            includeProfileOptions=False,
            username=user.get("username")
        )

        # Создаем данные пакета
        payload = {
            "contact": profile
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_INFO_BY_PHONE, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def ok_token(self, payload, seq, writer):
        """Получение токена для звонка"""
        # Валидируем данные пакета
        try:
            GetCallTokenPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.OK_TOKEN, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: когда-то взяться за звонки

        await self._send_error(seq, self.opcodes.OK_TOKEN, self.error_types.NOT_IMPLEMENTED, writer)

    async def msg_typing(self, payload, seq, writer, senderId):
        """Обработчик события печатания"""
        # Валидируем данные пакета
        try:
            TypingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        chatId = payload.get("chatId")
        type = payload.get("type") or "TYPING"

        # Ищем чат в базе данных
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                chat = await cursor.fetchone()

        # Если чат не найден, отправляем ошибку
        if not chat:
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.CHAT_NOT_FOUND, writer)
            return

        # Участники чата
        participants = await self.tools.get_chat_participants(chatId, self.db_pool)

        # Проверяем, является ли отправитель участником чата
        if int(senderId) not in participants:
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.CHAT_NOT_ACCESS, writer)
            return

        # Рассылаем событие участникам чата
        for participant in participants:
            if participant != senderId:
                # Если участник не является отправителем, отправляем
                await self.event(
                    participant,
                    {
                        "eventType": "typing",
                        "chatId": chatId,
                        "type": type,
                        "userId": senderId
                    }
                )

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.opcodes.MSG_TYPING
        )

        # Отправляем пакет
        await self._send(writer, packet)

    async def complain_reasons_get(self, payload, seq, writer):
        """Обработчик получения причин жалоб"""
        # Валидируем данные пакета
        try:
            ComplainReasonsGetPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.COMPLAIN_REASONS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Собираем данные пакета
        payload = {
            "complains": self.static.COMPLAIN_REASONS,
            "complainSync": int(time.time())
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.opcodes.COMPLAIN_REASONS_GET, payload=payload
        )

        # Отправляем пакет
        await self._send(writer, packet)

    async def chat_history(self, payload, seq, writer, senderId):
        """Обработчик получения истории чата"""
        # Валидируем данные пакета
        try:
            ChatHistoryPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        chatId = payload.get("chatId")
        forward = payload.get("forward", 0)
        backward = payload.get("backward", 0)
        from_time = payload.get("from", 0)
        getMessages = payload.get("getMessages", True)
        messages = []

        # Если пользователь хочет получить историю из избранного,
        # то выставляем в качестве ID чата его ID
        if chatId == 0: 
            chatId = senderId

        # Проверяем, существует ли чат
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Проверяем состоит ли пользователь в чате,
                # только в случае того, если это не избранное
                if chatId != senderId:
                    await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                    chat = await cursor.fetchone()

                    # Выбрасываем ошибку, если чата нет
                    if not chat:
                        await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.CHAT_NOT_FOUND, writer)
                        return

                    # Проверяем, является ли пользователь участником чата
                    participants = await self.tools.get_chat_participants(chatId, self.db_pool)
                    if int(senderId) not in participants:
                        await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.CHAT_NOT_ACCESS, writer)
                        return

                # Если запрошены сообщения
                if getMessages:
                    if backward > 0:
                        await cursor.execute(
                            "SELECT * FROM messages WHERE chat_id = %s AND time < %s ORDER BY id DESC LIMIT %s",
                            (chatId, from_time, backward)
                        )

                        result = await cursor.fetchall()

                        for row in result:
                            messages.append({
                                "id": row.get("id"),
                                "time": int(row.get("time")),
                                "type": row.get("type"),
                                "sender": row.get("sender"),
                                "text": row.get("text"),
                                "attaches": json.loads(row.get("attaches")),
                                "elements": json.loads(row.get("elements")),
                                "reactionInfo": {}
                            })

                    if forward > 0:
                        await cursor.execute(
                            "SELECT * FROM messages WHERE chat_id = %s AND time > %s ORDER BY id ASC LIMIT %s",
                            (chatId, from_time, forward)
                        )

                        result = await cursor.fetchall()

                        for row in result:
                            messages.append({
                                "id": row.get("id"),
                                "time": int(row.get("time")),
                                "type": row.get("type"),
                                "sender": row.get("sender"),
                                "text": row.get("text"),
                                "attaches": json.loads(row.get("attaches")),
                                "elements": json.loads(row.get("elements")),
                                "reactionInfo": {}
                            })

        # Формируем ответ
        payload = {
            "messages": messages
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_HISTORY, payload=payload
        )

        # Отправялем
        await self._send(writer, packet)
        
    async def profile(self, payload, seq, writer, userId, userPhone):
        # Валидируем входные данные
        try:
            UpdateProfilePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.PROFILE, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем поля из пакета (каждое может быть None)
        description = payload.get("description")
        firstName = payload.get("firstName")
        lastName = payload.get("lastName")

        # Обновляем только те поля, которые пришли в запросе
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if description is not None:
                    # При изменении описания также обновляем время последнего изменения профиля
                    await cursor.execute(
                        "UPDATE users SET description = %s, updatetime = %s WHERE id = %s",
                        (description, int(time.time() * 1000), userId)
                    )
                if firstName is not None:
                    await cursor.execute(
                        "UPDATE users SET firstname = %s WHERE id = %s",
                        (firstName, userId)
                    )
                if lastName is not None:
                    await cursor.execute(
                        "UPDATE users SET lastname = %s WHERE id = %s",
                        (lastName, userId)
                    )

                # Получаем актуальные данные пользователя после обновления
                await cursor.execute("SELECT * FROM users WHERE id = %s", (userId,))
                user = await cursor.fetchone()

        # Формируем URL аватарки если она есть
        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + str(photoId)

        # Генерируем профиль для отправки клиенту
        profile = self.tools.generate_profile(
            id=user.get("id"),
            phone=int(user.get("phone")),
            avatarUrl=avatar_url,
            photoId=photoId,
            updateTime=int(user.get("updatetime")),
            firstName=user.get("firstname"),
            lastName=user.get("lastname"),
            options=json.loads(user.get("options")),
            description=user.get("description"),
            accountStatus=int(user.get("accountstatus")),
            profileOptions=json.loads(user.get("profileoptions")),
            includeProfileOptions=True,
            username=user.get("username")
        )

        # Данные пакета
        payload = {
            "profile": profile
        }

        # Отправляем ответ на запрос (CMD_OK)
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.PROFILE, payload=payload
        )
        await self._send(writer, packet)

        # Отправляем всем сессиям о изменении профиля
        await self.event(
            user.get('id'),
            {
                "eventType": "profile_updated",
                "profile": profile,
                "writer": writer
            }     
        )

    async def chat_subscribe(self, payload, seq, writer):
        # Валидируем входные данные
        try:
            ChatSubscribePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.CHAT_SUBSCRIBE, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Созадаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_SUBSCRIBE, payload=None
        )

        # Отправялем
        await self._send(writer, packet)
