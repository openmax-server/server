from classes.baseprocessor import BaseProcessor

class SessionsProcessors(BaseProcessor):
    async def sessions_info(self, payload, seq, writer, senderPhone, hashedToken):
        """Получение активных сессий на аккаунте"""
        # Готовый список сессий
        sessions = []

        # Ищем сессии в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM tokens WHERE phone = %s", (str(senderPhone),))
                user_sessions = await cursor.fetchall()

        # Собираем сессии в список
        for session in user_sessions:
            sessions.append(
                {
                    "time": int(session.get("time")),
                    "client": f"MAX {session.get('device_type')}",
                    "info": session.get("device_name"),
                    "location": session.get("location"),
                    "current": True if session.get("token_hash") == hashedToken else False
                }
            )

        # Создаем данные пакета
        payload = {
            "sessions": sessions
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.SESSIONS_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)
