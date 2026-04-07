import pydantic
import json
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
            return None, None

        # Получаем данные из пакета
        deviceType = payload.get("userAgent").get("deviceType")
        deviceName = payload.get("userAgent").get("deviceName")

        # Данные пакета
        payload = {
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