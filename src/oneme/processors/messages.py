import pydantic
from classes.baseprocessor import BaseProcessor
from oneme.models import (
    TypingPayloadModel,
    SendMessagePayloadModel
)

class MessagesProcessors(BaseProcessor):
    async def msg_typing(self, payload, seq, writer, senderId):
        """Обработчик события печатания"""
        # Валидируем данные пакета
        try:
            TypingPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Извлекаем данные из пакета
        chatId = payload.get("chatId")
        type = payload.get("type") or "TYPING"

        # Ищем чат в базе данных
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                chat = await cursor.fetchone()

        # Если чат не найден, отправляем ошибку
        if not chat:
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.CHAT_NOT_FOUND, writer)
            return

        # Участники чата
        participants = await self.tools.get_chat_participants(chatId, self.db_pool)

        # Проверяем, является ли отправитель участником чата
        if int(senderId) not in participants:
            await self._send_error(seq, self.opcodes.MSG_TYPING, self.error_types.CHAT_NOT_ACCESS, writer)
            return

        # Рассылаем событие участникам чата
        for participant in participants:
            if participant != senderId:
                # Если участник не является отправителем, отправляем
                await self.event(
                    participant,
                    {
                        "eventType": "typing",
                        "chatId": chatId,
                        "type": type,
                        "userId": senderId
                    }
                )

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.opcodes.MSG_TYPING
        )

        # Отправляем пакет
        await self._send(writer, packet)

    async def msg_send(self, payload, seq, writer, senderId, db_pool):
        """Функция отправки сообщения"""
        # Валидируем данные пакета
        try:
            SendMessagePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Извлекаем данные из пакета
        userId = payload.get("userId")
        chatId = payload.get("chatId")
        message = payload.get("message")

        elements = message.get("elements") or []
        attaches = message.get("attaches") or []
        cid = message.get("cid") or 0
        text = message.get("text") or ""

        # Вычисляем ID чата по ID пользователя и ID отправителя, 
        # в случае отсутствия ID чата
        if not chatId:
            chatId = userId ^ senderId

        # Если клиент хочет отправить сообщение в избранное, 
        # то выставляем в качестве ID чата ID отправителя
        # (А ещё используем это, если клиент вообще ничего не указал)
        if chatId == 0 or not chatId:
            chatId = senderId
            participants = [senderId]
        else:
            # Если все таки клиент хочет отправить сообщение в нормальный чат,
            # то ищем его в базе данных (извлекать список участников все таки тоже надо)
            async with db_pool.acquire() as db_connection:
                async with db_connection.cursor() as cursor:
                    await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                    chat = await cursor.fetchone()

                    # Если нет такого чата - выбрасываем ошибку
                    if not chat:
                        await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.CHAT_NOT_FOUND, writer)
                        return
                    
                    # Список участников
                    participants = await self.tools.get_chat_participants(chatId, db_pool)

                    # Проверяем, является ли отправитель участником чата
                    if int(senderId) not in participants:
                        await self._send_error(seq, self.opcodes.MSG_SEND, self.error_types.CHAT_NOT_ACCESS, writer)
                        return

        # Добавляем сообщение в историю
        messageId, lastMessageId, messageTime = await self.tools.insert_message(
            chatId=chatId,
            senderId=senderId,
            text=text,
            attaches=attaches,
            elements=elements,
            cid=cid,
            type="USER",
            db_pool=self.db_pool
        )

        # Готовое тело сообщения
        bodyMessage = {
            "id": messageId,
            "time": messageTime,
            "type": "USER",
            "sender": senderId,
            "cid": cid,
            "text": text,
            "attaches": attaches,
            "elements": elements
        }

        # Отправляем событие всем участникам чата
        for participant in participants:
            await self.event(
                participant,
                {
                    "eventType": "new_msg",
                    "chatId": 0 if chatId == senderId else chatId,
                    "message": bodyMessage,
                    "prevMessageId": lastMessageId,
                    "time": messageTime,
                    "writer": writer
                }
            )

        # Данные пакета
        payload = {
            "chatId": 0 if chatId == senderId else chatId,
            "message": bodyMessage,
            "unread": 0,
            "mark": messageTime
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.MSG_SEND, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)