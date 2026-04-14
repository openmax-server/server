import hashlib
import json
import logging
import secrets
import time

import pydantic

from classes.baseprocessor import BaseProcessor
from common.sms import send_sms_code
from oneme.config import OnemeConfig
from oneme.models import (
    AuthConfirmRegisterPayloadModel,
    LoginPayloadModel,
    RequestCodePayloadModel,
    VerifyCodePayloadModel,
)


class AuthProcessors(BaseProcessor):
    def __init__(
        self,
        db_pool=None,
        clients=None,
        send_event=None,
        telegram_bot=None,
        type="socket",
    ):
        super().__init__(db_pool, clients, send_event, type)
        self.server_config = OnemeConfig().SERVER_CONFIG
        self.telegram_bot = telegram_bot

    async def auth_request(self, payload, seq, writer):
        """Обработчик запроса кода"""
        try:
            RequestCodePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(
                seq, self.opcodes.AUTH_REQUEST, self.error_types.INVALID_PAYLOAD, writer
            )
            return

        # Извлекаем телефон из пакета
        phone = payload.get("phone").replace("+", "").replace(" ", "").replace("-", "")

        # Генерируем токен
        token = secrets.token_urlsafe(102)
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
        local_fallback_code = False
        if self.config.sms_gateway_url:
            code = await send_sms_code(self.config.sms_gateway_url, phone)

            if code is None:
                code = str(secrets.randbelow(900000) + 100000)
                local_fallback_code = True
        else:
            code = str(secrets.randbelow(900000) + 100000)
            local_fallback_code = True

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
                        (
                            phone,
                            token_hash,
                            code_hash,
                            expires,
                        ),
                    )

                    # Если код был сгенерирован локально, а тг привязан к аккаунту - отправляем туда сообщение
                    if (
                        local_fallback_code
                        and self.telegram_bot
                        and user.get("telegram_id")
                    ):
                        await self.telegram_bot.send_code(
                            chat_id=int(user.get("telegram_id")), phone=phone, code=code
                        )
                else:
                    # Пользователь не найден - сохраняем токен со state='register'
                    # чтобы после верификации кода направить на экран регистрации
                    await cursor.execute(
                        "INSERT INTO auth_tokens (phone, token_hash, code_hash, expires, state) VALUES (%s, %s, %s, %s, %s)",
                        (
                            phone,
                            token_hash,
                            code_hash,
                            expires,
                            "register",
                        ),
                    )

        # Данные пакета
        payload = {
            "token": token,
            "codeLength": 6,
            "requestMaxDuration": 60000,
            "requestCountLeft": 10,
            "altActionDuration": 60000,
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK,
            seq=seq,
            opcode=self.opcodes.AUTH_REQUEST,
            payload=payload,
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
            await self._send_error(
                seq, self.opcodes.AUTH, self.error_types.INVALID_PAYLOAD, writer
            )
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
                    (hashed_token,),
                )
                stored_token = await cursor.fetchone()

                # Если токен просрочен, или его нет - отправляем ошибку
                if stored_token is None:
                    await self._send_error(
                        seq, self.opcodes.AUTH, self.error_types.CODE_EXPIRED, writer
                    )
                    return

                # Проверяем код
                if stored_token.get("code_hash") != hashed_code:
                    await self._send_error(
                        seq, self.opcodes.AUTH, self.error_types.INVALID_CODE, writer
                    )
                    return

                # Если это новый пользователь - переводим токен в state='verified'
                # и отдаём клиенту REGISTER токен, чтобы он показал экран ввода имени
                if stored_token.get("state") == "register":
                    await cursor.execute(
                        "UPDATE auth_tokens SET state = %s WHERE token_hash = %s",
                        (
                            "verified",
                            hashed_token,
                        ),
                    )
                    packet = self.proto.pack_packet(
                        cmd=self.proto.CMD_OK,
                        seq=seq,
                        opcode=self.opcodes.AUTH,
                        payload={
                            "tokenAttrs": {"REGISTER": {"token": token}},
                            "presetAvatars": [],
                        },
                    )
                    await self._send(writer, packet)
                    return

                # Ищем аккаунт
                await cursor.execute(
                    "SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),)
                )
                account = await cursor.fetchone()

                # Удаляем токен
                await cursor.execute(
                    "DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,)
                )

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        stored_token.get("phone"),
                        hashed_login,
                        deviceType,
                        deviceName,
                        "Little Saint James Island",
                        int(time.time()),
                    ),  # весь покрытый зеленью, абсолютно весь, остров невезения в океане есть
                )

        # Генерируем профиль
        # Аватарка с биографией
        photoId = (
            None if not account.get("avatar_id") else int(account.get("avatar_id"))
        )
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = (
            None if not account.get("description") else account.get("description")
        )

        # Собираем данные пакета
        payload = {
            "tokenAttrs": {"LOGIN": {"token": login}},
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
                username=account.get("username"),
            ),
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
            await self._send_error(
                seq, self.opcodes.AUTH_CONFIRM, self.error_types.INVALID_PAYLOAD, writer
            )
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
                    (
                        hashed_token,
                        "verified",
                    ),
                )
                stored_token = await cursor.fetchone()

                # Если токен не найден или просрочен - отправляем ошибку
                if stored_token is None:
                    await self._send_error(
                        seq,
                        self.opcodes.AUTH_CONFIRM,
                        self.error_types.CODE_EXPIRED,
                        writer,
                    )
                    return

                phone = stored_token.get("phone")

                # Проверяем что пользователь с таким телефоном ещё не существует
                await cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if await cursor.fetchone():
                    await self._send_error(
                        seq,
                        self.opcodes.AUTH_CONFIRM,
                        self.error_types.INVALID_PAYLOAD,
                        writer,
                    )
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
                        self.tools.generate_id(),
                        phone,
                        None,
                        first_name,
                        last_name,
                        None,
                        json.dumps([]),
                        json.dumps(["TT", "ONEME"]),
                        0,
                        str(now_ms),
                        str(now_s),
                    ),
                )

                user_id = cursor.lastrowid

                # Добавляем данные аккаунта
                await cursor.execute(
                    """
                    INSERT INTO user_data
                        (phone, contacts, folders, user_config, chat_config)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        phone,
                        json.dumps([]),
                        json.dumps(self.static.USER_FOLDERS),
                        json.dumps(self.static.USER_SETTINGS),
                        json.dumps({}),
                    ),
                )

                # Удаляем токен
                await cursor.execute(
                    "DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,)
                )

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        phone,
                        hashed_login,
                        deviceType or "ANDROID",
                        deviceName or "Unknown",
                        "Little Saint James Island",
                        now_s,
                    ),
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
            username=None,
        )

        # Собираем данные пакета
        payload = {
            "userToken": "0",
            "profile": profile,
            "tokenType": "LOGIN",
            "token": login,
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK,
            seq=seq,
            opcode=self.opcodes.AUTH_CONFIRM,
            payload=payload,
        )

        # Отправляем
        await self._send(writer, packet)
        self.logger.info(
            f"Новый пользователь зарегистрирован: phone={phone} id={user_id} name={first_name} {last_name}"
        )

    async def login(self, payload, seq, writer):
        """Обработчик авторизации клиента на сервере"""
        # Валидируем данные пакета
        try:
            LoginPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(
                seq, self.opcodes.LOGIN, self.error_types.INVALID_PAYLOAD, writer
            )
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
                await cursor.execute(
                    "SELECT * FROM tokens WHERE token_hash = %s", (hashed_token,)
                )
                token_data = await cursor.fetchone()

                # Если токен не найден, отправляем ошибку
                if token_data is None:
                    await self._send_error(
                        seq, self.opcodes.LOGIN, self.error_types.INVALID_TOKEN, writer
                    )
                    return

                # Ищем аккаунт пользователя в бд
                await cursor.execute(
                    "SELECT * FROM users WHERE phone = %s", (token_data.get("phone"),)
                )
                user = await cursor.fetchone()

                # Ищем данные пользователя в бд
                await cursor.execute(
                    "SELECT * FROM user_data WHERE phone = %s",
                    (token_data.get("phone"),),
                )
                user_data = await cursor.fetchone()

                # Ищем все чаты, где состоит пользователь
                await cursor.execute(
                    "SELECT * FROM chat_participants WHERE user_id = %s",
                    (user.get("id")),
                )
                user_chats = await cursor.fetchall()

                for chat in user_chats:
                    chats.append(chat.get("chat_id"))

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
            username=user.get("username"),
        )

        chats = await self.tools.generate_chats(
            chats, self.db_pool, user.get("id"), protocol_type=self.type
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
                "user": json.loads(user_data.get("user_config")),
            },
            "token": token,
            "videoChatHistory": False,
            "time": int(time.time() * 1000),
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
                await cursor.execute(
                    "DELETE FROM tokens WHERE token_hash = %s", (hashedToken,)
                )

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOGOUT, payload=None
        )

        # Отправляем
        await self._send(writer, response)
