# Импортирование библиотек
import ssl, logging, asyncio
from common.config import ServerConfig
from oneme_tcp.controller import OnemeMobileController
from telegrambot.controller import TelegramBotController
from tamtam_tcp.controller import TTMobileController
from tamtam_ws.controller import TTWSController
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
            autocommit=True
        )
    elif server_config.db_type == "sqlite":
        import aiosqlite
        raw_db = await aiosqlite.connect(server_config.db_file)
        db["acquire"] = raw_db

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
    async def api_event(target, eventData):
        for client in api.get("clients").get(target, {}).get("clients", {}):
            await controllers[client["protocol"]].event(target, client, eventData)
        
    set_logging()
    db = await init_db()
    ssl_context = init_ssl()
    clients = {}

    api = {
        "db": db,
        "ssl": ssl_context,
        "clients": clients,
        "event": api_event,
        "origins": server_config.origins
    }

    controllers = {
        "oneme_mobile": OnemeMobileController(),
        "tamtam_mobile": TTMobileController(),
        "tamtam_ws": TTWSController(),
        "telegrambot": TelegramBotController()
    }

    api["telegram_bot"] = controllers["telegrambot"]

    tasks = [
        controller.launch(api)
        for controller in controllers.values()
    ]

    # Запускаем контроллеры
    await asyncio.gather(*tasks)
    
if __name__ == "__main__":
    asyncio.run(main())