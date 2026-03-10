import json, random, secrets, hashlib, time, logging
from oneme_tcp.models import *
from oneme_tcp.proto import Proto
from oneme_tcp.config import OnemeConfig
from common.tools import Tools
from common.config import ServerConfig
from common.static import Static

class Processors:
    def __init__(self, db_pool=None, clients={}, send_event=None, telegram_bot=None):
        self.proto = Proto()
        self.tools = Tools()
        self.config = ServerConfig()
        self.static = Static()
        self.server_config = OnemeConfig().SERVER_CONFIG
        self.error_types = self.static.ErrorTypes()
        self.chat_types = self.static.ChatTypes()

        self.db_pool = db_pool
        self.event = send_event
        self.clients = clients
        self.telegram_bot = telegram_bot
        self.logger = logging.getLogger(__name__)

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

    async def process_hello(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.SESSION_INIT, self.error_types.INVALID_PAYLOAD, writer)
            return None, None

        # Получаем данные из пакета
        deviceType = payload.get("userAgent").get("deviceType")
        deviceName = payload.get("userAgent").get("deviceName")

        # Данные пакета
        payload = {
            "location": "RU",
            "app-update-type": 0, # 1 = принудительное обновление
            "reg-country-code": [
                # Список стран, который отдает официальный сервер
                "AZ", "AM", "KZ", "KG", "MD", "TJ", "UZ", "GE", "TH", "TR", 
                "TM", "AE", "LA", "MY", "ID", "CU", "KH", "VN", 

                # Список стран, который приделали уже мы                 
                "US", "CA", "UA"
            ],
            "phone-auto-complete-enabled": False,
            "lang": True
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.SESSION_INIT, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return deviceType, deviceName
    
    async def process_ping(self, payload, seq, writer):
        """Обработчик пинга"""
        # Валидируем данные пакета
        try:
            PingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.PING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.PING, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def process_telemetry(self, payload, seq, writer):
        """Обработчик телеметрии"""
        # TODO: можно было бы реализовать валидацию телеметрии, но сейчас это не особо важно

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.LOG, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def process_request_code(self, payload, seq, writer):
        """Обработчик запроса кода"""
        # Валидируем данные пакета
        try:
            RequestCodePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.AUTH_REQUEST, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем телефон из пакета
        phone = payload.get("phone").replace("+", "").replace(" ", "").replace("-", "")

        # Генерируем токен с кодом
        code = str(random.randint(100000, 999999))
        token = secrets.token_urlsafe(128)

        # Хешируем
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Время истечения токена
        expires = int(time.time()) + 300

        # Ищем пользователя, и если он существует, сохраняем токен
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
                user = await cursor.fetchone()

                # Если пользователя найден - сохраняем токен и отправляем код
                if user:
                    # Сохраняем токен
                    await cursor.execute("INSERT INTO auth_tokens (phone, token_hash, code_hash, expires) VALUES (%s, %s, %s, %s)", (phone, token_hash, code_hash, expires,))

                    # Если тг бот включен, и тг привязан к аккаунту - отправляем туда сообщение
                    if self.telegram_bot and user.get("telegram_id"):
                        await self.telegram_bot.send_code(chat_id=int(user.get("telegram_id")), phone=phone, code=code)
                    
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.AUTH_REQUEST, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        self.logger.debug(f"Код для {phone}: {code}")

    async def process_verify_code(self, payload, seq, writer, deviceType, deviceName):
        """Обработчик проверки кода"""
        # Валидируем данные пакета
        try:
            VerifyCodePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.AUTH, self.error_types.INVALID_PAYLOAD, writer)
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
                await cursor.execute("SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP()", (hashed_token,))
                stored_token = await cursor.fetchone()

                # Если токен просрочен, или его нет - отправляем ошибку
                if stored_token is None:
                    await self._send_error(seq, self.proto.AUTH, self.error_types.CODE_EXPIRED, writer)
                    return

                # Проверяем код
                if stored_token.get("code_hash") != hashed_code:
                    await self._send_error(seq, self.proto.AUTH, self.error_types.INVALID_CODE, writer)
                    return
                
                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Удаляем токен
                await cursor.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,))

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (stored_token.get("phone"), hashed_login, deviceType, deviceName, "Epstein Island", int(time.time()),)    
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.AUTH, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def process_login(self, payload, seq, writer):
        """Обработчик авторизации клиента на сервере"""
        # Валидируем данные пакета
        try:
            LoginPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.LOGIN, self.error_types.INVALID_PAYLOAD, writer)
            return
        
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
                    await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.INVALID_TOKEN, writer)
                    return

                # Ищем аккаунт пользователя в бд
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (token_data.get("phone"),))
                user = await cursor.fetchone()

                # Ищем данные пользователя в бд
                await cursor.execute("SELECT * FROM user_data WHERE phone = %s", (token_data.get("phone"),))
                user_data = await cursor.fetchone()

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
            json.loads(user_data.get("chats")),
            self.db_pool, user.get("id")
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.LOGIN, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return int(user.get("phone")), int(user.get("id")), hashed_token

    async def process_logout(self, seq, writer, hashedToken):
        """Обработчик завершения сессии"""
        # Удаляем токен из бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM tokens WHERE token_hash = %s", (hashedToken,))
        
        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.LOGOUT, payload=None
        )

        # Отправляем
        await self._send(writer, response)

    async def process_get_assets(self, payload, seq, writer):
        """Обработчик запроса ассетов клиента на сервере"""
        # Валидируем данные пакета
        try:
            AssetsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.ASSETS_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: сейчас это заглушка, а попозже нужно сделать полноценную реализацию

        # Данные пакета
        payload = {
            "sections": [],
            "sync": int(time.time() * 1000)
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.ASSETS_UPDATE, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def process_get_call_history(self, payload, seq, writer):
        """Обработчик получения истории звонков"""
        # Валидируем данные пакета
        try:
            GetCallHistoryPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.VIDEO_CHAT_HISTORY, self.error_types.INVALID_PAYLOAD, writer)
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.VIDEO_CHAT_HISTORY, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def process_send_message(self, payload, seq, writer, senderId, db_pool):
        """Функция отправки сообщения"""
        # Валидируем данные пакета
        try:
            SendMessagePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.MSG_SEND, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Извлекаем данные из пакета
        userId = payload.get("userId")
        chatId = payload.get("chatId")
        message = payload.get("message")

        elements = message.get("elements") or []
        attaches = message.get("attaches") or []
        cid = message.get("cid") or 0
        text = message.get("text") or ""

        # Если клиент вообще ничего не указал в пакете, то выбрасываем ошибку
        if not all([userId, chatId, elements, attaches, cid, text]):
            await self._send_error(seq, self.proto.MSG_SEND, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Время отправки сообщения
        messageTime = int(time.time() * 1000)

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
                        await self._send_error(seq, self.proto.MSG_SEND, self.error_types.CHAT_NOT_FOUND, writer)
                        return
                    
                    # Список участников
                    participants = json.loads(chat.get("participants"))

                    # Проверяем, является ли отправитель участником чата
                    if int(senderId) not in participants:
                        await self._send_error(seq, self.proto.MSG_SEND, self.error_types.CHAT_NOT_ACCESS, writer)
                        return

        # Добавляем сообщение в историю
        messageId, lastMessageId = await self.tools.insert_message(
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
                    "time": messageTime
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.MSG_SEND, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def process_get_folders(self, payload, seq, writer, senderPhone):
        """Синхронизация папок с сервером"""
        # Валидируем данные пакета
        try:
            SyncFoldersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.FOLDERS_GET, self.error_types.INVALID_PAYLOAD, writer)
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.FOLDERS_GET, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def process_get_sessions(self, payload, seq, writer, senderPhone, hashedToken):
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.SESSIONS_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def process_search_users(self, payload, seq, writer):
        """Поиск пользователей по ID"""
        # Валидируем данные пакета
        try:
            SearchUsersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.CONTACT_INFO, self.error_types.INVALID_PAYLOAD, writer)
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
            seq=seq, opcode=self.proto.CONTACT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def process_search_chats(self, payload, seq, writer, senderId):
        """Поиск чатов по ID"""
        # Валидируем данные пакета
        try:
            SearchChatsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.CHAT_INFO, self.error_types.INVALID_PAYLOAD, writer)
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
                            # Если чат - диалог, и пользователь в нем не состоит,
                            # то продолжаем без добавления результата
                            if chat.get("type") == self.chat_types.DIALOG and senderId not in json.loads(chat.get("participants")):
                                continue 

                            # Получаем последнее сообщение из чата
                            message, messageTime = await self.tools.get_last_message(
                                chatId, self.db_pool
                            )

                            # Добавляем чат в список
                            chats.append(
                                self.tools.generate_chat(
                                    chatId, chat.get("owner"), 
                                    chat.get("type"), json.loads(chat.get("participants")),
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.CHAT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def process_search_by_phone(self, payload, seq, writer, senderId):
        """Поиск по номеру телефона"""
        # Валидируем данные пакета
        try:
            SearchByPhonePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.CONTACT_INFO_BY_PHONE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Ищем пользователя в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (int(payload.get("phone")),))
                user = await cursor.fetchone()

                # Если пользователь не найден, отправляем ошибку
                if not user:
                    await self._send_error(seq, self.proto.CONTACT_INFO_BY_PHONE, self.error_types.USER_NOT_FOUND, writer)
                    return
                
                # ID чата
                chatId = senderId ^ user.get("id")

                # Ищем диалог в бд
                await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                chat = await cursor.fetchone()

                # Если диалога нет - создаем
                if not chat:
                    await cursor.execute(
                        "INSERT INTO chats (id, owner, type, participants) VALUES (%s, %s, %s, %s)",
                        (chatId, senderId, "DIALOG", json.dumps([int(senderId), int(user.get("id"))]))
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.CONTACT_INFO_BY_PHONE, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def process_get_call_token(self, payload, seq, writer):
        """Получение токена для звонка"""
        # Валидируем данные пакета
        try:
            GetCallTokenPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.OK_TOKEN, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # TODO: когда-то взяться за звонки

        await self._send_error(seq, self.proto.OK_TOKEN, self.error_types.NOT_IMPLEMENTED, writer)

    async def process_typing(self, payload, seq, writer, senderId):
        """Обработчик события печатания"""
        # Валидируем данные пакета
        try:
            TypingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.MSG_TYPING, self.error_types.INVALID_PAYLOAD, writer)
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
            await self._send_error(seq, self.proto.MSG_TYPING, self.error_types.CHAT_NOT_FOUND, writer)
            return

        # Участники чата
        participants = json.loads(chat.get("participants"))

        # Проверяем, является ли отправитель участником чата
        if int(senderId) not in participants:
            await self._send_error(seq, self.proto.MSG_TYPING, self.error_types.CHAT_NOT_ACCESS, writer)
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
            seq=seq, opcode=self.proto.MSG_TYPING
        )

        # Отправляем пакет
        await self._send(writer, packet)

    async def process_complain_reasons_get(self, payload, seq, writer):
        """Обработчик получения причин жалоб"""
        # Валидируем данные пакета
        try:
            ComplainReasonsGetPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.proto.COMPLAIN_REASONS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Собираем данные пакета
        payload = {
            "complains": self.static.COMPLAIN_REASONS,
            "complainSync": int(time.time())
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.proto.COMPLAIN_REASONS_GET, payload=payload
        )

        # Отправляем пакет
        await self._send(writer, packet)