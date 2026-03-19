import logging
import random
import json
import time
from telebot.async_telebot import AsyncTeleBot
from textwrap import dedent
from common.static import Static
from common.sql_queries import SQLQueries
from common.tools import Tools

class TelegramBot:
    def __init__(self, token, enabled, db_pool, whitelist_ids=None):
        self.bot = AsyncTeleBot(token)
        self.tools = Tools()
        self.enabled = enabled
        self.db_pool = db_pool
        self.whitelist_ids = whitelist_ids if whitelist_ids is not None else []
        self.logger = logging.getLogger(__name__)

        self.msg_types = Static().BotMessageTypes()
        self.static = Static()
        self.sql_queries = SQLQueries()

        @self.bot.message_handler(commands=['start'])
        async def handle_start(message):
            tg_id = str(message.from_user.id)

            # Ищем привязанный аккаунт пользователя            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(self.sql_queries.SELECT_USER_BY_TG_ID, (tg_id,))
                    account = await cursor.fetchone()

            if account:
                # Извлекаем id аккаунта с телефоном
                phone = account.get('phone')
                
                await self.bot.send_message(
                    message.chat.id,
                    self.get_bot_message(self.msg_types.WELCOME_ALREADY_REGISTERED).format(phone=phone)
                )
            else:
                await self.bot.send_message(
                    message.chat.id, self.get_bot_message(self.msg_types.WELCOME_NEW_USER)
                )

        @self.bot.message_handler(commands=['register'])
        async def handle_register(message):
            tg_id = str(message.from_user.id)
            
            # Проверка ID на наличие в белом списке
            if tg_id not in self.whitelist_ids:
                await self.bot.send_message(message.chat.id, self.get_bot_message(self.msg_types.ID_NOT_WHITELISTED))
                return
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Проверка на существование
                    await cursor.execute(self.sql_queries.SELECT_USER_BY_TG_ID, (tg_id,))
                    if await cursor.fetchone():
                        await self.bot.send_message(
                            message.chat.id, 
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
                                self.tools.generate_user_id(),
                                new_phone, # phone
                                tg_id, # telegram_id
                                message.from_user.first_name[:59], # firstname
                                (message.from_user.last_name or "")[:59], # lastname
                                (message.from_user.username or "")[:60], # username
                                json.dumps([]), # profileoptions
                                json.dumps(["TT", "ONEME"]), # options
                                0, # accountstatus
                                updatetime,
                                lastseen,
                            )
                        )
                        
                        # Добавляем данные о аккаунте
                        await cursor.execute(
                            self.sql_queries.INSERT_USER_DATA,
                            (
                                new_phone, # phone
                                json.dumps([]), # chats
                                json.dumps([]), # contacts
                                json.dumps(self.static.USER_FOLDERS), # folders
                                json.dumps(self.static.USER_SETTINGS), # user settings
                                json.dumps({}), # chat_config
                            )
                        )

                        await self.bot.send_message(
                            message.chat.id,
                            self.get_bot_message(self.msg_types.REGISTRATION_SUCCESS).format(new_phone=new_phone)
                        )
                    except Exception as e:
                        self.logger.error(f"Ошибка при регистрации: {e}")
                        await self.bot.send_message(
                            message.chat.id, 
                            self.get_bot_message(self.msg_types.INTERNAL_ERROR)
                        )
    
    def get_bot_message(self, msg_type):
        return dedent(self.static.BOT_MESSAGES.get(msg_type)).strip()

    async def start(self):
        if self.enabled == True:
            try:
                await self.bot.polling()
            except Exception as e:
                self.logger.error(f"Ошибка запуска Telegram бота: {e}")
        else:
            self.logger.warning("Запуск Telegram бота отключен")

    async def send_auth_code(self, chat_id, phone, code):
        try:
            await self.bot.send_message(
                chat_id, self.get_bot_message(self.msg_types.INCOMING_CODE).format(phone=phone, code=code)
            )
        except Exception as e:
            self.logger.error(f"Ошибка отправки кода в Telegram: {e}")