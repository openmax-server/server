import pydantic
import json
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import (
    HelloPayloadModel,
    PingPayloadModel,
    UpdateProfilePayloadModel
)


class MainProcessors(BaseProcessor):
    def __init__(self, db_pool=None, clients=None, send_event=None, type="socket"):
        super().__init__(db_pool, clients, send_event, type)

    async def session_init(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.SESSION_INIT, self.error_types.INVALID_PAYLOAD, writer)
            return None, None, None

        # Получаем данные из пакета
        userAgent = payload.get("userAgent")
        deviceType = userAgent.get("deviceType")
        deviceName = userAgent.get("deviceName")
        appVersion = userAgent.get("appVersion")

        # Данные пакета
        payload = {
            "callsSeed": int(time.time() * 1000),
            "location": "RU",
            "app-update-type": 0,  # 1 = принудительное обновление
            "reg-country-code": self.static.REG_COUNTRY_CODES,
            "phone-auto-complete-enabled": False,
            "qr-auth-enabled": False,
            "lang": True
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSION_INIT, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return deviceType, deviceName, appVersion
    
    async def ping(self, payload, seq, writer, userId=None):
        """Обработчик пинга"""
        # Валидируем данные пакета
        try:
            PingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.PING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Обновляем статус пользователя, если он авторизован
        # и в пакете отправлен интерактив
        interactive = payload.get("interactive") if payload else None
        if userId and interactive is not None:
            now = int(time.time())
            user = self.clients.get(userId)
            if user:
                if interactive:
                    user["status"] = 2
                    user["last_seen"] = now
                else:
                    user["status"] = 0
                    user["last_seen"] = now

                # Сохраняем последнее время посещения
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            "UPDATE users SET lastseen = %s WHERE id = %s",
                            (str(now), userId)
                        )

                # Рассылаем статус контактам пользователя
                now_ms = int(time.time() * 1000)
                if interactive:
                    presence_data = {"on": "ON", "seen": now, "status": 1}
                else:
                    presence_data = {"seen": now}

                # Находим всех, у кого этот пользователь в контактах
                async with self.db_pool.acquire() as conn2:
                    async with conn2.cursor() as cursor2:
                        await cursor2.execute(
                            "SELECT owner_id FROM contacts WHERE contact_id = %s",
                            (userId,)
                        )
                        contact_owners = await cursor2.fetchall()

                # Рассылаем
                for row in contact_owners:
                    owner_id = int(row.get("owner_id"))
                    if owner_id in self.clients:
                        await self.event(
                            owner_id,
                            {
                                "eventType": "presence",
                                "userId": userId,
                                "presence": presence_data,
                                "time": now_ms,
                            }
                        )

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

    async def profile(self, payload, seq, writer, userId):
        # Валидируем входные данные
        try:
            UpdateProfilePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.PROFILE, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Ищем пользователя в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id = %s", (userId,))
                user = await cursor.fetchone()

                # Если пользователь не найден
                if not user:
                    await self._send_error(seq, self.opcodes.PROFILE, self.error_types.USER_NOT_FOUND, writer)
                    return

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

        # Создаем данные пакета
        payload = {
            "profile": profile
        }

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.PROFILE, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def update_config(self, payload, seq, writer, userPhone, hashedToken=None):
        """
            Обработчик 22 опкода (config)
            Он отвечает за обновление настроек приватности
            и пуш токена для пушей
        """
        # Пейлоад, который отдадим клиенту
        # а отдавать его нужно только при изменении настроек приватности
        result_payload = None

        if payload.get("pushToken"):
            push_token = payload.get("pushToken")
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE tokens SET push_token = %s WHERE phone = %s AND token_hash = %s",
                        (push_token, str(userPhone), hashedToken)
                    )
        elif payload.get("settings") and payload.get("settings").get("user"):
            """Обновление настроек приватности"""
            new_settings = payload.get("settings").get("user")

            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Получаем текущий конфиг
                    await cursor.execute(
                        "SELECT user_config FROM user_data WHERE phone = %s", (userPhone,)
                    )
                    row = await cursor.fetchone()

                    if row:
                        current_config = json.loads(row.get("user_config"))

                        # Обновляем настройки
                        for key, value in new_settings.items():
                            if key in current_config:
                                current_config[key] = value

                        # Сохраняем обновлённый конфиг
                        await cursor.execute(
                            "UPDATE user_data SET user_config = %s WHERE phone = %s",
                            (json.dumps(current_config), userPhone)
                        )

                        result_payload = {
                            "user": current_config,
                            "hash": "0"
                        }

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONFIG, payload=result_payload
        )

        # Отправляем
        await self._send(writer, response)