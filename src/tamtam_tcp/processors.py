import hashlib, secrets, random, time, logging, json # PEP-8 по приколу сделан >_<
import re
from common.static import Static
from common.tools import Tools
from tamtam_tcp.proto import Proto
from tamtam_tcp.models import *

class Processors:
    def __init__(self, db_pool=None, clients={}, send_event=None):
        self.static = Static()
        self.proto = Proto()
        self.tools = Tools()
        self.error_types = self.static.ErrorTypes()
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def _send(self, writer, packet):
        try:
            writer.write(packet)
            await writer.drain()
        except:
            pass

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
        except Exception as e:
            await self._send_error(seq, self.proto.HELLO, self.error_types.INVALID_PAYLOAD, writer)
            return None, None
        
        # Получаем данные из пакета
        deviceType = payload.get("userAgent").get("deviceType")
        deviceName = payload.get("userAgent").get("deviceName")

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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.HELLO, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)
        return deviceType, deviceName
    
    async def process_request_code(self, payload, seq, writer):
        """Обработчик запроса кода"""
        # Валидируем данные пакета
        try:
            RequestCodePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.proto.REQUEST_CODE, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем телефон из пакета
        phone = re.sub(r'\D', '', payload.get("phone", "")) # Не хардкодим, через регулярки

        # Генерируем токен с кодом
        code = f"{secrets.randbelow(1_000_000):06d}" # Старая версия ненадежна, могла отбросить ведущие нули или вообще интерпритировать как систему счисления с основанием 8
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

                if user is None:
                    await self._send_error(seq, self.proto.REQUEST_CODE, self.error_types.USER_NOT_FOUND, writer)
                    return

                # Сохраняем токен
                await cursor.execute("INSERT INTO auth_tokens (phone, token_hash, code_hash, expires, state) VALUES (%s, %s, %s, %s, %s)", (phone, token_hash, code_hash, expires, "started",))

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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.REQUEST_CODE, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

        self.logger.debug(f"Код для {phone}: {code}")

    async def process_verify_code(self, payload, seq, writer):
        """Обработчик проверки кода"""
        # Валидируем данные пакета
        try:
            VerifyCodePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.INVALID_PAYLOAD, writer)
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
                await cursor.execute("SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP()", (hashed_token,))
                stored_token = await cursor.fetchone()

                if stored_token is None:
                    await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.CODE_EXPIRED, writer)
                    return

                # Проверяем код
                if stored_token.get("code_hash") != hashed_code:
                    await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.INVALID_CODE, writer)
                    return
                
                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Обновляем состояние токена
                await cursor.execute("UPDATE auth_tokens set state = %s WHERE token_hash = %s", ("verified", hashed_token,))

                # # Создаем сессию
                # await cursor.execute(
                #     "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                #     (stored_token.get("phone"), hashed_login, deviceType, deviceName, "Epstein Island", int(time.time()),)    
                # )

        # Генерируем профиль
        # Аватарка с биографией
        photoId = None if not account.get("avatar_id") else int(account.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not account.get("description") else account.get("description")

        # Собираем данные пакета
        payload = {
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
                includeProfileOptions=False,
                username=account.get("username"),
                type="TT"
            ).get("contact"),
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
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.VERIFY_CODE, payload=payload
        )

        await self._send(writer, packet)

    async def process_final_auth(self, payload, seq, writer, deviceType, deviceName):
        """Обработчик финальной аутентификации"""
        # Валидируем данные пакета
        try:
            FinalAuthPayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.proto.FINAL_AUTH, self.error_types.INVALID_PAYLOAD, writer)
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
                await cursor.execute("SELECT * FROM auth_tokens WHERE token_hash = %s AND expires > UNIX_TIMESTAMP()", (hashed_token,))
                stored_token = await cursor.fetchone()

                if stored_token is None:
                    await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.INVALID_TOKEN, writer)
                    return

                if stored_token.get("state") == "started":
                    await self._send_error(seq, self.proto.VERIFY_CODE, self.error_types.INVALID_TOKEN, writer)
                    return

                # Ищем аккаунт
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (stored_token.get("phone"),))
                account = await cursor.fetchone()

                # Обновляем состояние токена
                await cursor.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (hashed_token,))

                # Создаем сессию
                await cursor.execute(
                    "INSERT INTO tokens (phone, token_hash, device_type, device_name, location, time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (stored_token.get("phone"), hashed_login, deviceType, deviceName, "Epstein Island", int(time.time()),)    
                )

        # Аватарка с биографией
        photoId = None if not account.get("avatar_id") else int(account.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not account.get("description") else account.get("description")

        # Собираем данные пакета
        payload = {
            "userToken": "0",
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
                includeProfileOptions=False,
                username=account.get("username"),
                type="TT"
            ).get("contact"),
            "tokenType": "LOGIN",
            "token": login
        }

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.proto.FINAL_AUTH, payload=payload
        )

        await self._send(writer, packet)