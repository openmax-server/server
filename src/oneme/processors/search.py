import json
import pydantic
from classes.baseprocessor import BaseProcessor
from oneme.models import (
    SearchUsersPayloadModel,
    SearchChatsPayloadModel,
    SearchByPhonePayloadModel
)


class SearchProcessors(BaseProcessor):
    async def contact_info(self, payload, seq, writer, senderId):
        """Поиск пользователей по ID"""
        # Валидируем данные пакета
        try:
            SearchUsersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_INFO, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Итоговый список пользователей
        users = []

        # ID пользователей, которые нам предстоит найти
        contactIds = payload.get("contactIds")

        # Ищем пользователей в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for contactId in contactIds:
                    await cursor.execute("SELECT * FROM users WHERE id = %s", (contactId,))
                    user = await cursor.fetchone()

                    # Если такой пользователь есть, добавляем его в список
                    if user:
                        # Аватарка с биографией
                        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
                        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
                        description = None if not user.get("description") else user.get("description")

                        # Получаем данные контакта
                        await cursor.execute(
                            "SELECT * FROM contacts WHERE owner_id = %s AND contact_id = %s",
                            (senderId, contactId),
                        )
                        contact_row = await cursor.fetchone()
                        custom_firstname = contact_row.get("custom_firstname") if contact_row else None
                        custom_lastname = contact_row.get("custom_lastname") if contact_row else None
                        blocked = bool(contact_row.get("is_blocked")) if contact_row else False

                        # Генерируем профиль
                        users.append(
                            self.tools.generate_profile(
                                id=user.get("id"),
                                phone=int(user.get("phone")),
                                avatarUrl=avatar_url,
                                photoId=photoId,
                                updateTime=int(user.get("updatetime")),
                                firstName=user.get("firstname"),
                                lastName=user.get("lastname"),
                                options=json.loads(user.get("options")),
                                description=description,
                                accountStatus=int(user.get("accountstatus")),
                                profileOptions=json.loads(user.get("profileoptions")),
                                includeProfileOptions=False,
                                username=user.get("username"),
                                custom_firstname=custom_firstname,
                                custom_lastname=custom_lastname,
                                blocked=blocked,
                            )
                        )

        # Создаем данные пакета
        payload = {
            "contacts": users
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def contact_info_by_phone(self, payload, seq, writer, senderId):
        """Поиск по номеру телефона"""
        # Валидируем данные пакета
        try:
            SearchByPhonePayloadModel.model_validate(payload)
        except Exception as e:
            await self._send_error(seq, self.opcodes.CONTACT_INFO_BY_PHONE, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Ищем пользователя в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE phone = %s", (int(payload.get("phone")),))
                user = await cursor.fetchone()

                # Если пользователь не найден, отправляем ошибку
                if not user:
                    await self._send_error(seq, self.opcodes.CONTACT_INFO_BY_PHONE, self.error_types.USER_NOT_FOUND, writer)
                    return
                
                # ID чата
                chatId = senderId ^ user.get("id")

                # Ищем диалог в бд
                await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                chat = await cursor.fetchone()

                # Если диалога нет - создаем
                if not chat:
                    await cursor.execute(
                        "INSERT INTO chats (id, owner, type) VALUES (%s, %s, %s)",
                        (chatId, senderId, "DIALOG")
                    )

                    # Добавляем участников в таблицу chat_participants
                    participants = [int(senderId), int(user.get("id"))]
                    
                    for user_id in participants:
                        await cursor.execute(
                            "INSERT INTO chat_participants (chat_id, user_id) VALUES (%s, %s)",
                            (chatId, user_id)
                        )

        # Аватарка с биографией
        photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
        avatar_url = None if not photoId else self.config.avatar_base_url + photoId
        description = None if not user.get("description") else user.get("description")

        # Получаем данные контакта
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM contacts WHERE owner_id = %s AND contact_id = %s",
                    (senderId, user.get("id")),
                )
                contact_row = await cursor.fetchone()
        custom_firstname = contact_row.get("custom_firstname") if contact_row else None
        custom_lastname = contact_row.get("custom_lastname") if contact_row else None
        blocked = bool(contact_row.get("is_blocked")) if contact_row else False

        # Генерируем профиль
        profile = self.tools.generate_profile(
            id=user.get("id"),
            phone=int(user.get("phone")),
            avatarUrl=avatar_url,
            photoId=photoId,
            updateTime=int(user.get("updatetime")),
            firstName=user.get("firstname"),
            lastName=user.get("lastname"),
            options=json.loads(user.get("options")),
            description=description,
            accountStatus=int(user.get("accountstatus")),
            profileOptions=json.loads(user.get("profileoptions")),
            includeProfileOptions=False,
            username=user.get("username"),
            custom_firstname=custom_firstname,
            custom_lastname=custom_lastname,
            blocked=blocked,
        )

        # Создаем данные пакета
        payload = {
            "contact": profile
        }

        # Создаем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_INFO_BY_PHONE, payload=payload
        )

        # Отправляем
        await self._send(writer, response)

    async def chat_info(self, payload, seq, writer, senderId):
        """Поиск чатов по ID"""
        # Валидируем данные пакета
        try:
            SearchChatsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CHAT_INFO, self.error_types.INVALID_PAYLOAD, writer)
            return

        # Итоговый список чатов
        chats = []

        # ID чатов, которые нам предстоит найти
        chatIds = payload.get("chatIds")

        # Ищем чаты в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for chatId in chatIds:
                    if chatId != 0:
                        await cursor.execute("SELECT * FROM chats WHERE id = %s", (chatId,))
                        chat = await cursor.fetchone()
                        
                        if chat:
                            # Проверяем, является ли пользователь участником чата
                            participants = await self.tools.get_chat_participants(chatId, self.db_pool)
                            # (в max нельзя смотреть и отправлять сообщения в чат, в котором ты не участник, в отличие от tg (например, комментарии в каналах),
                            # так что надо тоже так делать)
                            if int(senderId) not in participants:
                                continue

                            # Получаем последнее сообщение из чата
                            message, messageTime = await self.tools.get_last_message(
                                chatId, self.db_pool, protocol_type=self.type
                            )

                            # Добавляем чат в список
                            chats.append(
                                self.tools.generate_chat(
                                    chatId, chat.get("owner"),
                                    chat.get("type"), participants,
                                    message, messageTime
                                )
                            )
                    else:
                        # Получаем последнее сообщение из чата
                        message, messageTime = await self.tools.get_last_message(
                            senderId, self.db_pool, protocol_type=self.type
                        )

                        # ID избранного
                        chatId = senderId ^ senderId

                        # Добавляем чат в список
                        chats.append(
                            self.tools.generate_chat(
                                chatId, senderId, 
                                "DIALOG", [senderId],
                                message, messageTime
                            )
                        )

        # Создаем данные пакета
        payload = {
            "chats": chats
        }

        # Собираем пакет
        response = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CHAT_INFO, payload=payload
        )

        # Отправляем
        await self._send(writer, response)
