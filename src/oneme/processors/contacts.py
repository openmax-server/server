import pydantic
from classes.baseprocessor import BaseProcessor
from oneme.models import ContactListPayloadModel

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
