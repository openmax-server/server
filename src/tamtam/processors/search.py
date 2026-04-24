import json, pydantic
from classes.baseprocessor import BaseProcessor
from tamtam.models import SearchUsersPayloadModel

class SearchProcessors(BaseProcessor):
    async def contact_info(self, payload, seq, writer):
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
                        photo_id = None if not user.get("avatar_id") else int(user.get("avatar_id"))
                        avatar_url = None if not photo_id else self.config.avatar_base_url + photo_id
                        description = None if not user.get("description") else user.get("description")

                        # Генерируем профиль
                        users.append(
                            self.tools.generate_profile_tt(
                                id=user.get("id"),
                                phone=int(user.get("phone")),
                                avatarUrl=avatar_url,
                                photoId=photo_id,
                                updateTime=int(user.get("updatetime")),
                                firstName=user.get("firstname"),
                                lastName=user.get("lastname"),
                                options=json.loads(user.get("options")),
                                description=description,
                                username=user.get("username")
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