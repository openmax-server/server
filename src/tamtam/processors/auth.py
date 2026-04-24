import hashlib
import secrets
import time
import json
import re
from classes.baseprocessor import BaseProcessor
from tamtam.models import (
    RequestCodePayloadModel,
    VerifyCodePayloadModel,
    FinalAuthPayloadModel,
    LoginPayloadModel,
)
from tamtam.config import TTConfig

class AuthProcessors(BaseProcessor):
    def __init__(self, db_pool=None, clients=None, send_event=None, type="socket"):
        super().__init__(db_pool, clients, send_event, type)
        self.server_config = TTConfig().SERVER_CONFIG

    async def auth_request(self, payload, seq, writer):
        """Обработчик запроса кода"""
        # Валидируем данные пакета
        try:
            RequestCodePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.AUTH_REQUEST,
                                   self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем телефон из пакета
        phone = re.sub(r'\D', '', payload.get("phone", ""))

        # Генерируем токен с кодом
        code = f"{secrets.randbelow(1_000_000):06d}"
        token = secrets.token_urlsafe(128)

        # Хешируем
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Срок жизни токена (5 минут)
        expires = int(time.time()) + 300

        # Ищем пользователя, и если он существует, сохраняем токен
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
                user = await cursor.fetchone()

                # Если пользователь существует, сохраняем токен
                if user:
                    await cursor.execute(
                        "INSERT INTO auth_tokens (phone, token_hash, code_hash, expires, state) VALUES (%s, %s, %s, %s, %s)",
                        (phone, token_hash, code_hash, expires, "started")
                    )

        # Данные пакета
        payload = {
            "verifyToken": token,
            "retries": 5,
            "codeDelay": 60,
            "codeLength": 6,
            "callDelay": 0,
            "requestType": "SMS"
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH_REQUEST, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        self.logger.debug(f"Код для {phone}: {code}")

    async def auth(self, payload, seq, writer):
        """Обработчик проверки кода"""
        # Валидируем данные пакета
        try:
            VerifyCodePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.AUTH,
                                   self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        code = payload.get("verifyCode")
        token = payload.get("token")

        # Хешируем токен с кодом
        hashed_code = hashlib.sha256(code.encode()).hexdigest()
        hashed_token = hashlib.sha256(token.encode()).hexdigest()

        # Ищем токен с кодом
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Ищем токен
                await cursor.execute(
                    "SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP()",
                    (hashed_token,)
                )
                stored_token = await cursor.fetchone()

                if not stored_token:
                    await self._send_error(seq, self.opcodes.AUTH,
                                           self.error_types.CODE_EXPIRED, writer)
                    return

                # Проверяем код
                if stored_token.get("code_hash") != hashed_code:
                    await self._send_error(seq, self.opcodes.AUTH,
                                           self.error_types.INVALID_CODE, writer)
                    return

                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Обновляем состояние токена
                await cursor.execute(
                    "UPDATE auth_tokens set state = %s WHERE token_hash = %s",
                    ("verified", hashed_token)
                )

        # Генерируем профиль
        # Аватарка с биографией
        photo_id = int(account["avatar_id"]) if account.get("avatar_id") else None
        avatar_url = f"{self.config.avatar_base_url}{photo_id}" if photo_id else None
        description = account.get("description")

        # Собираем данные пакета
        payload = {
            "profile": self.tools.generate_profile_tt(
                id=account.get("id"),
                phone=int(account.get("phone")),
                avatarUrl=avatar_url,
                photoId=photo_id,
                updateTime=int(account.get("updatetime")),
                firstName=account.get("firstname"),
                lastName=account.get("lastname"),
                options=json.loads(account.get("options")),
                description=description,
                username=account.get("username")
            ),
            "tokenAttrs": {
                "AUTH": {
                    "token": token
                }
            },
            "tokenTypes": {
                "AUTH": token
            }
        }

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH, payload=payload
        )

        await self._send(writer, packet)

    async def auth_confirm(self, payload, seq, writer, deviceType, deviceName):
        """Обработчик финальной аутентификации"""
        # Валидируем данные пакета
        try:
            FinalAuthPayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.AUTH_CONFIRM,
                                   self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        token = payload.get("token")

        if not deviceType:
            deviceType = payload.get("deviceType")

        # Хешируем токен
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

                if stored_token is None:
                    await self._send_error(seq, self.opcodes.AUTH_CONFIRM,
                                           self.error_types.INVALID_TOKEN, writer)
                    return

                # Если авторизация только началась - отдаем ошибку
                if stored_token.get("state") == "started":
                    await self._send_error(seq, self.opcodes.AUTH_CONFIRM,
                                           self.error_types.INVALID_TOKEN, writer)
                    return

                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Удаляем токен
                await cursor.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,))

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (stored_token.get("phone"), hashed_login, deviceType, deviceName,
                     "Epstein Island", int(time.time()))
                )

        # Аватарка с биографией
        photo_id = None if not account.get("avatar_id") else int(account.get("avatar_id"))
        avatar_url = None if not photo_id else self.config.avatar_base_url + str(photo_id)
        description = None if not account.get("description") else account.get("description")

        # Собираем данные пакета
        payload = {
            "userToken": "0",  # Пока как заглушка
            "profile": self.tools.generate_profile_tt(
                id=account.get("id"),
                phone=int(account.get("phone")),
                avatarUrl=avatar_url,
                photoId=photo_id,
                updateTime=int(account.get("updatetime")),
                firstName=account.get("firstname"),
                lastName=account.get("lastname"),
                options=json.loads(account.get("options")),
                description=description,
                username=account.get("username")
            ),
            "tokenType": "LOGIN",
            "token": login
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.AUTH_CONFIRM, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def login(self, payload, seq, writer):
        """Обработчик авторизации клиента на сервере"""
        # Валидируем данные пакета
        try:
            LoginPayloadModel.model_validate(payload)
        except Exception as e:
            self.logger.error(f"Возникли ошибки при валидации пакета: {e}")
            await self._send_error(seq, self.opcodes.LOGIN,
                                   self.error_types.INVALID_PAYLOAD, writer)
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
                    await self._send_error(seq, self.opcodes.LOGIN,
                                           self.error_types.INVALID_TOKEN, writer)
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

                # Обновляем юзер конфиг
                updated_user_config = await self.tools.update_user_config(
                    cursor, token_data.get("phone"),
                    user_data.get("user_config"), self.static.USER_SETTINGS
                )

        # Аватарка с биографией
        photo_id = None if not user.get("avatar_id") else int(user.get("avatar_id"))
        avatar_url = None if not photo_id else self.config.avatar_base_url + str(photo_id)
        description = None if not user.get("description") else user.get("description")

        # Генерируем профиль
        profile = self.tools.generate_profile_tt(
            id=user.get("id"),
            phone=int(user.get("phone")),
            avatarUrl=avatar_url,
            photoId=photo_id,
            updateTime=int(user.get("updatetime")),
            firstName=user.get("firstname"),
            lastName=user.get("lastname"),
            options=json.loads(user.get("options")),
            description=description,
            username=user.get("username")
        )

        chats = await self.tools.generate_chats(
            chats, self.db_pool, user.get("id"),
            include_favourites=False
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
                "hash": "e5903aa8-0000000000000000-80000106-0000000000000001-00000001-0000000000000000-00000000-2-00000001-0000019c9559d057",
                "server": self.server_config,
                "user": updated_user_config,
                "chatFolders": {
                    "FOLDERS": [],
                    "ALL_FILTER_EXCLUDE": []
                }
            },
            "token": token,
            "calls": [],
            "videoChatHistory": False,
            "drafts": {
                "chats": {
                    "discarded": {},
                    "saved": {}
                },
                "users": {
                    "discarded": {},
                    "saved": {}
                }
            },
            "time": int(time.time() * 1000)
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOGIN, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return int(user.get("phone")), int(user.get("id")), hashed_token