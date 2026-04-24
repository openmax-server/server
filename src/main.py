# Импортирование библиотек
import asyncio
import logging
import ssl

from common.config import ServerConfig
from common.push import PushService
from oneme.controller import OnemeController
from tamtam.controller import TTController
from telegrambot.controller import TelegramBotController

# Конфиг сервера
server_config = ServerConfig()


class SQLiteCursorCompat:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = None

    async def __aenter__(self):
        self.cursor = await self.connection.cursor()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.cursor is not None:
            await self.cursor.close()
        self.cursor = None

    @property
    def lastrowid(self):
        return None if self.cursor is None else self.cursor.lastrowid

    def _normalize_query(self, query):
        return query.replace("%s", "?").replace(
            "UNIX_TIMESTAMP()", "CAST(strftime('%s','now') AS INTEGER)"
        )

    async def execute(self, query, params=()):
        normalized_query = self._normalize_query(query)
        if params is None:
            params = ()
        elif not isinstance(params, (tuple, list, dict)):
            params = (params,)
        await self.cursor.execute(normalized_query, params)

    async def fetchone(self):
        row = await self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self):
        rows = await self.cursor.fetchall()
        return [dict(row) for row in rows]


class SQLiteConnectionCompat:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return SQLiteCursorCompat(self.connection)


class SQLitePoolCompat:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return SQLiteConnectionCompat(self.connection)


async def init_db():
    """Инициализация базы данных"""

    db = {}

    if server_config.db_type == "mysql":
        import aiomysql

        db = await aiomysql.create_pool(
            host=server_config.db_host,
            port=server_config.db_port,
            user=server_config.db_user,
            password=server_config.db_password,
            db=server_config.db_name,
            cursorclass=aiomysql.DictCursor,
            autocommit=True,
        )
    elif server_config.db_type == "sqlite":
        import aiosqlite

        raw_db = await aiosqlite.connect(server_config.db_file, isolation_level=None)
        raw_db.row_factory = aiosqlite.Row
        db = SQLitePoolCompat(raw_db)

    # Возвращаем
    return db


def init_ssl():
    """Создание контекста SSL"""
    # Создаем контекст SSL
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(server_config.certfile, server_config.keyfile)

    # Возвращаем
    return ssl_context


def set_logging():
    """Настройка уровня логирования"""
    # Настройка уровня логирования
    log_level = server_config.log_level

    if log_level == "debug":
        logging.basicConfig(level=logging.DEBUG)
    elif log_level == "info":
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=None)


async def main():
    """Запуск сервера"""

    set_logging()
    db = await init_db()
    ssl_context = init_ssl()
    clients = {}
    push_service = PushService(server_config.firebase_credentials_path)

    async def api_event(target, eventData):
        target_clients = api.get("clients", {}).get(target, {}).get("clients", [])

        for client in target_clients:
            await controllers[client["protocol"]].event(target, client, eventData)

        # Если у пользователя нет активных подключений
        # и это новое сообщение - отсылаем пуш
        if not target_clients and eventData.get("eventType") == "new_msg":
            message = eventData.get("message", {})
            sender_id = message.get("sender")
            text = message.get("text", "")
            chat_id = eventData.get("chatId", "")
            msg_id = message.get("id", 0)
            await push_service.send_to_user(
                db, target,
                sender_id=sender_id,
                msg_id=msg_id,
                chat_id=chat_id,
                text=text,
            )

    api = {
        "db": db,
        "ssl": ssl_context,
        "clients": clients,
        "event": api_event,
        "origins": server_config.origins,
    }

    controllers = {
        "oneme": OnemeController(),
        "tamtam": TTController(),
        "telegrambot": TelegramBotController(),
    }

    api["telegram_bot"] = controllers["telegrambot"]

    tasks = [controller.launch(api) for controller in controllers.values()]

    # Запускаем контроллеры
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
