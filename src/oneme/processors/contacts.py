import pydantic
import json
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import ContactListPayloadModel, ContactPresencePayloadModel, ContactUpdatePayloadModel

class ContactsProcessors(BaseProcessor):
    async def contact_list(self, payload, seq, writer, userId):
        """Обработчик получения контактов"""
        # Валидируем данные пакета
        try:
            ContactListPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_LIST, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        status = payload.get("status")
        count = payload.get("count")

        # Итоговый контакт-лист
        contact_list = []

        if status == "BLOCKED":
            # Собираем контакты, которые в черном списке
            blocked = []

            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if count:
                        await cursor.execute(
                            "SELECT * FROM contacts WHERE owner_id = %s AND is_blocked = TRUE LIMIT %s",
                            (userId, count),
                        )
                    else:
                        await cursor.execute(
                            "SELECT * FROM contacts WHERE owner_id = %s AND is_blocked = TRUE",
                            (userId,),
                        )
                    rows = await cursor.fetchall()

                    for row in rows:
                        blocked.append(
                            {
                                "id": int(row.get("contact_id")),
                                "firstname": row.get("custom_firstname"),
                                "lastname": row.get("custom_lastname"),
                                "blocked": True,
                            }
                        )

            # Генерируем контакт-лист
            contact_list = await self.tools.generate_contacts(
                blocked, self.db_pool, avatar_base_url=self.config.avatar_base_url
            )

        # Собираем данные пакета
        response_payload = {
            "contacts": contact_list
        }

        # Создаем пакет
        packet = self.proto.pack_packet(
            seq=seq, opcode=self.opcodes.CONTACT_LIST, payload=response_payload
        )

        # Отправляем пакет
        await self._send(writer, packet)

    async def contact_update(self, payload, seq, writer, userId):
        """
            Обработчик опкода какого-то там 
            (их хуй запомнишь, даже в мриме команды помню, бля)

            Отвечает за добавку, удаление, блокировку и разблокировку контакта
        """
        # Валидируем данные пакета
        try:
            ContactUpdatePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return

        action = payload.get("action")
        contactId = payload.get("contactId")
        firstName = payload.get("firstName")
        lastName = payload.get("lastName", "")

        if action == "ADD":
            # Проверяем, существует ли пользователь с таким ID
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM users WHERE id = %s", (contactId,))
                    user = await cursor.fetchone()

                    if not user:
                        await self._send_error(seq, self.opcodes.CONTACT_UPDATE, self.error_types.USER_NOT_FOUND, writer)
                        return

                    # Проверяем, не добавлен ли уже контакт
                    await cursor.execute(
                        "SELECT * FROM contacts WHERE owner_id = %s AND contact_id = %s",
                        (userId, contactId)
                    )
                    row = await cursor.fetchone()

                    # Если контакта не существует, то можем продолжать,
                    if not row:
                        # Добавляем контакт
                        await cursor.execute(
                            "INSERT INTO contacts (owner_id, contact_id, custom_firstname, custom_lastname, is_blocked) VALUES (%s, %s, %s, %s, FALSE)",
                            (userId, contactId, firstName, lastName)
                        )
                    # а если уже существует, отправляем ошибку
                    else:
                        await self._send_error(seq, self.opcodes.CONTACT_UPDATE, self.error_types.CONTACT_ALREADY_EXISTS, writer)
                        return

            # Генерируем профиль
            photoId = None if not user.get("avatar_id") else int(user.get("avatar_id"))
            avatar_url = None if not photoId else self.config.avatar_base_url + str(photoId)

            contact = self.tools.generate_profile(
                id=user.get("id"),
                phone=int(user.get("phone")),
                avatarUrl=avatar_url,
                photoId=photoId,
                updateTime=int(user.get("updatetime")),
                firstName=user.get("firstname"),
                lastName=user.get("lastname"),
                options=json.loads(user.get("options")),
                accountStatus=int(user.get("accountstatus")),
                includeProfileOptions=False,
                custom_firstname=firstName,
                custom_lastname=lastName,
            )

            response_payload = {
                "contact": contact
            }

            packet = self.proto.pack_packet(
                cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_UPDATE, payload=response_payload
            )

            await self._send(writer, packet)

        elif action == "REMOVE":
            # Удаляем контакт
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "DELETE FROM contacts WHERE owner_id = %s AND contact_id = %s",
                        (userId, contactId)
                    )

            packet = self.proto.pack_packet(
                cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_UPDATE, payload=None
            )

            await self._send(writer, packet)

    async def contact_presence(self, payload, seq, writer):
        """Обработчик получения статуса контактов"""
        # Валидируем данные пакета
        try:
            ContactPresencePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.CONTACT_PRESENCE, self.error_types.INVALID_PAYLOAD, writer)
            return

        contact_ids = payload.get("contactIds", [])
        now_ms = int(time.time() * 1000)

        presence = await self.tools.collect_presence(contact_ids, self.clients, self.db_pool)

        response_payload = {
            "presence": presence,
            "time": now_ms
        }

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.CONTACT_PRESENCE, payload=response_payload
        )

        await self._send(writer, packet)
