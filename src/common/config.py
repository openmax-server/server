import os
from dotenv import load_dotenv

load_dotenv()

class ServerConfig:
    def __init__(self):
        pass

    ### Адрес сервера
    host = os.getenv("host") or "0.0.0.0"

    ### Для мобилок
    oneme_tcp_port = int(os.getenv("oneme_tcp_port") or 443)
    tamtam_tcp_port = int(os.getenv("tamtam_tcp_port") or 4433)

    ### Шлюзы для веба
    oneme_ws_port = int(os.getenv("oneme_ws_port") or 81)
    tamtam_ws_port = int(os.getenv("tamtam_ws_port") or 82)

    ### Уровень отладки
    log_level = os.getenv("log_level") or "debug"

    ### Тип базы данных
    db_type = os.getenv("db_type") or "mysql"

    ### MySQL
    db_host = os.getenv("db_host") or "127.0.0.1"
    db_port = int(os.getenv("db_port") or 3306)
    db_user = os.getenv("db_user") or "root"
    db_password = os.getenv("db_password") or "qwerty"
    db_name = os.getenv("db_name") or "openmax"

    ### SQLite
    db_file = os.getenv("db_file") or "openmax.db"

    ### SSL
    certfile = os.getenv("certfile") or "cert.pem"
    keyfile = os.getenv("keyfile") or "key.pem"

    ### Avatar base url
    avatar_base_url = os.getenv("avatar_base_url") or "http://127.0.0.1/avatar/"

    ### Telegram bot
    telegram_bot_token = os.getenv("telegram_bot_token") or "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    telegram_bot_enabled = bool(os.getenv("telegram_bot_enabled")) or True
    telegram_whitelist_ids = [x.strip() for x in os.getenv("telegram_whitelist_ids", "").split(",") if x.strip()]