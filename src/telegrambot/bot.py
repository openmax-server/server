import logging
import random
import json
import time
from telebot.async_telebot import AsyncTeleBot

class TelegramBot:
    def __init__(self, token, enabled, db_pool, whitelist_ids=None):
        self.bot = AsyncTeleBot(token)
        self.enabled = enabled
        self.db_pool = db_pool
        self.whitelist_ids = whitelist_ids if whitelist_ids is not None else []
        self.logger = logging.getLogger(__name__)

        @self.bot.message_handler(commands=['start'])
        async def handle_start(message):
            tg_id = str(message.from_user.id)

            # Ищем привязанный аккаунт пользователя            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
                    account = await cursor.fetchone()

            if account:
                # Извлекаем id аккаунта с телефоном
                phone = account.get('phone')
                
                await self.bot.send_message(
                    message.chat.id,
                    f"👋 С возвращением в OpenMAX!\nВаш номер, если забыли: {phone}"
                )
                await self.send_auth_code(message.chat.id, phone)
            else:
                await self.bot.send_message(
                    message.chat.id, 
                    "👋 Добро пожаловать на этот инстанс OpenMAX!\nУ вас ещё нет аккаунта. Используйте /register для создания."
                )

        @self.bot.message_handler(commands=['register'])
        async def handle_register(message):
            tg_id = str(message.from_user.id)
            
            # Проверка ID на наличие в белом списке
            if self.whitelist_ids and tg_id not in self.whitelist_ids:
                await self.bot.send_message(message.chat.id, "❌ Ваш ID не находится в белом списке.")
                return
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Проверка на существование
                    await cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (tg_id,))
                    if await cursor.fetchone():
                        await self.bot.send_message(message.chat.id, "⚠️ У вас уже есть аккаунт! Существующий аккаунт можно удалить через клиент или обратившись к администратору инстанса.")
                        return

                    # Подготовка данных согласно схеме
                    new_phone = f"7900{random.randint(1000000, 9999999)}"
                    updatetime = str(int(time.time() * 1000))
                    lastseen = str(int(time.time()))
                    
                    folders = {
                        "folders": [], 
                        "foldersOrder": [], 
                        "allFilterExcludeFolders": []
                    }

                    user_settings = {
                        "CHATS_PUSH_NOTIFICATION": "ON",
                        "PUSH_DETAILS": True,
                        "PUSH_SOUND": "DEFAULT",
                        "INACTIVE_TTL": "6M",
                        "CHATS_QUICK_REPLY": False,
                        "SHOW_READ_MARK": True,
                        "AUDIO_TRANSCRIPTION_ENABLED": True,
                        "CHATS_LED": 65535,
                        "SEARCH_BY_PHONE": "ALL",
                        "INCOMING_CALL": "ALL",
                        "DOUBLE_TAP_REACTION_DISABLED": False,
                        "SAFE_MODE_NO_PIN": False,
                        "CHATS_PUSH_SOUND": "DEFAULT",
                        "DOUBLE_TAP_REACTION_VALUE": None,
                        "FAMILY_PROTECTION": "OFF",
                        "LED": 65535,
                        "HIDDEN": False,
                        "VIBR": True,
                        "CHATS_INVITE": "ALL",
                        "PUSH_NEW_CONTACTS": False,
                        "UNSAFE_FILES": True,
                        "DONT_DISTURB_UNTIL": 0,
                        "CHATS_VIBR": True,
                        "CONTENT_LEVEL_ACCESS": False,
                        "STICKERS_SUGGEST": "ON",
                        "SAFE_MODE": False,
                        "M_CALL_PUSH_NOTIFICATION": "ON",
                        "QUICK_REPLY": False
                    }

                    try:
                        # Создаем юзера
                        await cursor.execute(
                            """
                                INSERT INTO users 
                                (phone, telegram_id, firstname, lastname, username, 
                                 profileoptions, options, accountstatus, updatetime, lastseen) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
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
                            """
                                INSERT INTO user_data
                                (phone, chats, contacts, folders, user_config, chat_config)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                new_phone, # phone
                                json.dumps([]), # chats
                                json.dumps([]), # contacts
                                json.dumps(folders), # folders
                                json.dumps(user_settings), # user_config
                                json.dumps({}), # chat_config
                            )
                        )

                        await self.bot.send_message(
                            message.chat.id,
                            f"✅ Регистрация завершена!\nВаш новый номер: {new_phone}\nВсе коды для авторизации будут приходить сюда."
                        )
                    except Exception as e:
                        self.logger.error(f"Ошибка при регистрации: {e}")
                        await self.bot.send_message(message.chat.id, "❌ Ошибка при регистрации аккаунта. Обратитесь к администратору инстанса за помощью.")
    
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
                chat_id,
                f"Новая попытка входа в OpenMAX с вашим номером {phone}\nКод: {code}\n❗️ Никому не сообщайте его, иначе можете потерять свой аккаунт!"
            )
        except Exception as e:
            self.logger.error(f"Ошибка отправки кода в Telegram: {e}")