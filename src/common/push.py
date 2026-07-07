import asyncio
import logging
import time
import firebase_admin
from firebase_admin import credentials, messaging

class PushService:
    def __init__(self, credentials_path):
        self.logger = logging.getLogger(__name__)

        if not credentials_path:
            self.logger.warning("Огненная база сегодня не работает, укажите путь к файлу с ключами")
            self.enabled = False
            return

        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        self.enabled = True
        self.logger.info("Огненная база инициализирована")

    async def send(self, push_token, data):
        """Отправка пуша"""
        if not self.enabled:
            return None

        str_data = {k: str(v) for k, v in data.items() if v is not None}

        message = messaging.Message(
            data=str_data,
            token=push_token,
            android=messaging.AndroidConfig(
                priority="high",
            ),
        )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, messaging.send, message)
            self.logger.debug(f"Отправил пуш: {response}")
            return response
        except messaging.UnregisteredError:
            self.logger.warning(f"Пуш-токен не зарегистрирован: {push_token}")
            return None
        except Exception as e:
            self.logger.error(f"Не удалось отправить пуш: {e}")
            return None

    async def send_to_user(self, db_pool, phone, sender_id=None, msg_id=None,
                           chat_id=None, text="", is_group=False):
        """Отправка пушей на все устройства пользователя"""
        if not self.enabled:
            return

        # Получаем имя отправителя
        user_name = ""
        if sender_id:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT firstname, lastname FROM users WHERE id = %s",
                        (sender_id,)
                    )
                    sender = await cursor.fetchone()
                    if sender:
                        firstname = sender.get("firstname", "")
                        lastname = sender.get("lastname", "")
                        user_name = f"{firstname} {lastname}".strip()

        now_ms = str(int(time.time() * 1000))
        msg_type = "ChatMessage" if is_group else "Message"
        data = {
            "type": msg_type,
            "msgid": str(msg_id) if msg_id else "0",
            "suid": str(sender_id) if sender_id else None,
            "mc": str(chat_id) if chat_id else None,
            "msg": text,
            "userName": user_name,
            "ttime": now_ms,
            "ctime": now_ms,
        }

        # Получаем все пуш-токены пользователя
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT push_token FROM tokens WHERE phone = %s AND push_token IS NOT NULL",
                    (phone,)
                )
                rows = await cursor.fetchall()

        for row in rows:
            await self.send(row["push_token"], data)
