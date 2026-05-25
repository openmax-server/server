import logging
from typing import List, Dict, Any, Optional

class Database:
    """
    Класс для управления асинхронными операциями с базой данных.
    Реализует паттерн работы через пул соединений (aiomysql) или прямое соединение (aiosqlite).
    """

    def __init__(self, db_pool: Any, db_type: str = "mysql"):
        self.pool = db_pool
        self.db_type = db_type
        self.logger = logging.getLogger(__name__)

    async def get_recent_chats(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получает список последних чатов, в которых участвовал пользователь.
        
        Оптимизировано: используется JOIN вместо вложенных SELECT для повышения производительности.
        Использует индекс idx_messages_sender_chat.
        """
        query = """
            SELECT DISTINCT c.* 
            FROM chats c
            INNER JOIN messages m ON c.id = m.chat_id
            WHERE m.sender = %s
            ORDER BY m.id DESC
            LIMIT %s
        """
        
        # Для SQLite синтаксис плейсхолдеров отличается (?)
        # Но в проекте в основном используется mysql стиль (%s) судя по sql_queries.py
        placeholder = "?" if self.db_type == "sqlite" else "%s"
        query = query.replace("%s", placeholder)

        try:
            if self.db_type == "mysql":
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, (user_id, limit))
                        return await cur.fetchall()
            else:
                # В aiosqlite 'acquire' — это само соединение (согласно main.py)
                async with self.pool["acquire"].execute(query, (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    # Превращаем в dict, так как aiosqlite возвращает кортежи по умолчанию
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении get_recent_chats: {e}")
            return []

    async def add_message(self, chat_id: int, sender_id: int, text: str, type: str = "text") -> bool:
        """Добавление нового сообщения в базу данных."""
        # Заглушка для демонстрации
        return True
