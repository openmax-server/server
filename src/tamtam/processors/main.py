import json
import pydantic
from classes.baseprocessor import BaseProcessor
from tamtam.models import HelloPayloadModel, PingPayloadModel
from tamtam.models import UpdateProfilePayloadModel

class MainProcessors(BaseProcessor):
    async def session_init(self, payload, seq, writer):
        """Обработчик приветствия"""
        # Валидируем данные пакета
        try:
            HelloPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            await self._send_error(seq, self.opcodes.SESSION_INIT,
                                   self.error_types.INVALID_PAYLOAD, writer)
            return None, None

        # Получаем данные из пакета
        device_type = payload.get("userAgent").get("deviceType")
        device_name = payload.get("userAgent").get("deviceName")

        # Данные пакета
        payload = {
            "proxy": "",
            "logs-enabled": False,
            "proxy-domains": [],
            "location": "RU",
            "libh-enabled": False,
            "phone-auto-complete-enabled": False
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSION_INIT, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return device_type, device_name

    async def profile(self, payload, seq, writer, userId):
        """Обработчик получения/обновления профиля"""
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
                photo_id = int(user["avatar_id"]) if user.get("avatar_id") else None
                avatar_url = f"{self.config.avatar_base_url}{photo_id}" if photo_id else None
                description = user.get("description")

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
        """Обработчик обновления настроек и пуш-токена"""
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
            new_settings = payload.get("settings").get("user")

            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT user_config FROM user_data WHERE phone = %s", (userPhone,)
                    )
                    row = await cursor.fetchone()

                    if row:
                        current_config = json.loads(row.get("user_config"))

                        for key, value in new_settings.items():
                            if key in current_config:
                                current_config[key] = value

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
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.PING, payload=None
        )

        # Отправляем
        await self._send(writer, packet)

    async def log(self, payload, seq, writer):
        """Обработчик лога"""
        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.LOG, payload=None
        )

        # Отправляем
        await self._send(writer, packet)