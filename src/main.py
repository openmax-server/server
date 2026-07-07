# Импортирование библиотек
import asyncio
import logging
import signal
import ssl
import sys
import traceback

from common.config import ServerConfig
from common.push import PushService
from common.sqlite import SQLitePoolCompat
from oneme.controller import OnemeController
from tamtam.controller import TTController
from telegrambot.controller import TelegramBotController

# Конфиг сервера
server_config = ServerConfig()

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

    loop = asyncio.get_running_loop()
    running_tasks = []

    def _shutdown(sig):
        logging.info(f"Получен сигнал {sig}, завершаем все задачи...")
        for task in running_tasks:
            task.cancel()

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _shutdown, sig)

    coros = [controller.launch(api) for controller in controllers.values()]
    running_tasks.extend(asyncio.create_task(coro) for coro in coros)

    # Запускаем контроллеры
    try:
        await asyncio.gather(*running_tasks)
    except asyncio.CancelledError:
        logging.info("Все задачи завершены")
    except Exception as e:
        logging.error(
            f"Произошла неизвестная ошибка: {e}"
        )
        traceback.print_exc()
    finally:
        if hasattr(db, 'close'):
            db.close()
            await db.wait_closed()
        elif hasattr(db, 'connection') and hasattr(db.connection, 'close'):
            await db.connection.close()


if __name__ == "__main__":
    asyncio.run(main())

