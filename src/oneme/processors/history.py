import pydantic
import json
from classes.baseprocessor import BaseProcessor
from oneme.models import ChatHistoryPayloadModel

class HistoryProcessors(BaseProcessor):
    async def chat_history(self, payload, seq, writer, senderId):
        """Обработчик получения истории чата"""
        # Валидируем данные пакета
        try:
            ChatHistoryPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        chatId = payload.get("chatId")
        forward = payload.get("forward", 0)
        backward = payload.get("backward", 0)
        from_time = payload.get("from", 0)
        getMessages = payload.get("getMessages", True)
        messages = []

        # Если пользователь хочет получить историю из избранного,
        # то выставляем в качестве ID чата его ID
        if chatId == 0: 
            chatId = senderId

        # Проверяем, существует ли чат
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Проверяем состоит ли пользователь в чате,
                # только в случае того, если это не избранное
                if chatId != senderId:
                    await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                    chat = await cursor.fetchone()

                    # Выбрасываем ошибку, если чата нет
                    if not chat:
                        await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.CHAT_NOT_FOUND, writer)
                        return

                    # Проверяем, является ли пользователь участником чата
                    participants = await self.tools.get_chat_participants(chatId, self.db_pool)
                    if int(senderId) not in participants:
                        await self._send_error(seq, self.opcodes.CHAT_HISTORY, self.error_types.CHAT_NOT_ACCESS, writer)
                        return

                # Если запрошены сообщения
                if getMessages:
                    if backward > 0:
                        await cursor.execute(
                            "SELECT * FROM messages WHERE chat_id = %s AND time < %s ORDER BY time ASC LIMIT %s",
                            (chatId, from_time, backward)
                        )

                        result = await cursor.fetchall()

                        for row in result:
                            # TODO: Сборку тела сообщения нужно вынести в отдельную функцию
                            messages.append({
                                "id": row.get("id") if self.type == 'mobile' else str(row.get('id')),
                                "time": int(row.get("time")),
                                "type": row.get("type"),
                                "sender": row.get("sender"),
                                "text": row.get("text"),
                                "attaches": json.loads(row.get("attaches")),
                                "elements": json.loads(row.get("elements")),
                                "reactionInfo": {},
                                "options": 1,
                            })

                    if forward > 0:
                        await cursor.execute(
                            "SELECT * FROM messages WHERE chat_id = %s AND time > %s ORDER BY time ASC LIMIT %s",
                            (chatId, from_time, forward)
                        )

                        result = await cursor.fetchall()

                        for row in result:
                            messages.append({
                                "id": row.get("id"),
                                "time": int(row.get("time")),
                                "type": row.get("type"),
                                "sender": row.get("sender"),
                                "text": row.get("text"),
                                "attaches": json.loads(row.get("attaches")),
                                "elements": json.loads(row.get("elements")),
                                "reactionInfo": {}
                            })

        # Сортируем сообщения по времени
        messages.sort(key=lambda x: x["time"])

        # Формируем ответ
        payload = {
            "messages": messages
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_HISTORY, payload=payload
        )

        # Отправялем
        await self._send(writer, packet)