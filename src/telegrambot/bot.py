import json
import logging
import random
import time
from textwrap import dedent

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from common.sql_queries import SQLQueries
from common.static import Static
from common.tools import Tools


class TelegramBot:
    def __init__(self, token, enabled, db_pool, whitelist_ids=None):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
        self.tools = Tools()
        self.enabled = enabled
        self.db_pool = db_pool
        self.whitelist_ids = whitelist_ids if whitelist_ids is not None else []
        self.logger = logging.getLogger(__name__)

        self.msg_types = Static().BotMessageTypes()
        self.static = Static()
        self.sql_queries = SQLQueries()

        self.router.message.register(self.handle_start, Command("start"))
        self.router.message.register(self.handle_register, Command("register"))

    def get_bot_message(self, msg_type):
        return dedent(self.static.BOT_MESSAGES.get(msg_type)).strip()

    async def handle_start(self, message: Message):
        tg_id = str(message.from_user.id)

        # Ищем привязанный аккаунт пользователя
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(self.sql_queries.SELECT_USER_BY_TG_ID, (tg_id,))
                account = await cursor.fetchone()

        if account:
            # Извлекаем id аккаунта с телефоном
            phone = account.get("phone")

            await message.answer(
                self.get_bot_message(self.msg_types.WELCOME_ALREADY_REGISTERED).format(
                    phone=phone
                )
            )
        else:
            await message.answer(self.get_bot_message(self.msg_types.WELCOME_NEW_USER))

    async def handle_register(self, message: Message):
        tg_id = str(message.from_user.id)

        # Проверка ID на наличие в белом списке
        if tg_id not in self.whitelist_ids:
            await message.answer(
                self.get_bot_message(self.msg_types.ID_NOT_WHITELISTED)
            )
            return

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Проверка на существование
                await cursor.execute(self.sql_queries.SELECT_USER_BY_TG_ID, (tg_id,))
                if await cursor.fetchone():
                    await message.answer(
                        self.get_bot_message(self.msg_types.ACCOUNT_ALREADY_EXISTS)
                    )
                    return

                # Подготовка данных согласно схеме
                new_phone = f"7900{random.randint(1000000, 9999999)}"
                updatetime = str(int(time.time() * 1000))
                lastseen = str(int(time.time()))

                try:
                    # Создаем юзера
                    await cursor.execute(
                        self.sql_queries.INSERT_USER,
                        (
                            self.tools.generate_id(),
                            new_phone,  # phone
                            tg_id,  # telegram_id
                            message.from_user.first_name[:59],  # firstname
                            (message.from_user.last_name or "")[:59],  # lastname
                            (message.from_user.username or "")[:60],  # username
                            json.dumps([]),  # profileoptions
                            json.dumps(["TT", "ONEME"]),  # options
                            0,  # accountstatus
                            updatetime,
                            lastseen,
                        ),
                    )

                    # Добавляем данные о аккаунте
                    await cursor.execute(
                        self.sql_queries.INSERT_USER_DATA,
                        (
                            new_phone,  # phone
                            json.dumps([]),  # contacts
                            json.dumps(self.static.USER_FOLDERS),  # folders
                            json.dumps(self.static.USER_SETTINGS),  # user settings
                            json.dumps({}),  # chat_config
                        ),
                    )

                    await message.answer(
                        self.get_bot_message(
                            self.msg_types.REGISTRATION_SUCCESS
                        ).format(new_phone=new_phone)
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка при регистрации: {e}")
                    await message.answer(
                        self.get_bot_message(self.msg_types.INTERNAL_ERROR)
                    )

    async def start(self):
        if self.enabled:
            try:
                await self.dp.start_polling(self.bot)
            except Exception as e:
                self.logger.error(f"Ошибка запуска Telegram бота: {e}")
        else:
            self.logger.warning("Запуск Telegram бота отключен")

    async def send_auth_code(self, chat_id, phone, code):
        try:
            await self.bot.send_message(
                chat_id,
                self.get_bot_message(self.msg_types.INCOMING_CODE).format(
                    phone=phone, code=code
                ),
            )
        except Exception as e:
            self.logger.error(f"Ошибка отправки кода в Telegram: {e}")
