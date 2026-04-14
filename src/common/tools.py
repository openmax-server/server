import hashlib
import json
import random
import time


class Tools:
    def __init__(self):
        pass

    def generate_profile(
        self,
        id=1,
        phone=70000000000,
        avatarUrl=None,
        photoId=None,
        updateTime=0,
        firstName="Test",
        lastName="Account",
        options=[],
        description=None,
        accountStatus=0,
        profileOptions=[],
        includeProfileOptions=True,
        username=None,
    ):
        contact = {
            "id": id,
            "updateTime": updateTime,
            "phone": phone,
            "names": [
                {
                    "name": firstName,
                    "firstName": firstName,
                    "lastName": lastName,
                    "type": "ONEME",
                }
            ],
            "options": options,
            "accountStatus": accountStatus,
        }

        if avatarUrl:
            contact["photoId"] = photoId
            contact["baseUrl"] = avatarUrl
            contact["baseRawUrl"] = avatarUrl

        if description:
            contact["description"] = description

        if username:
            contact["link"] = "https://max.ru/" + username

        if includeProfileOptions:
            return {"contact": contact, "profileOptions": profileOptions}
        else:
            return contact

    def generate_profile_tt(
        self,
        id=1,
        phone=70000000000,
        avatarUrl=None,
        photoId=None,
        updateTime=0,
        firstName="Test",
        lastName="Account",
        options=[],
        description=None,
        username=None,
    ):
        contact = {
            "id": id,
            "updateTime": updateTime,
            "phone": phone,
            "names": [{"name": f"{firstName} {lastName}", "type": "TT"}],
            "options": options,
        }

        if avatarUrl:
            contact["photoId"] = photoId
            contact["baseUrl"] = avatarUrl
            contact["baseRawUrl"] = avatarUrl

        if description:
            contact["description"] = description

        if username:
            contact["link"] = "https://tamtam.chat/" + username

        return contact

    def generate_chat(
        self, id, owner, type, participants, lastMessage, lastEventTime, prevMessageId=0
    ):
        """Генерация чата"""
        # Генерируем список участников
        if isinstance(participants, dict):
            result_participants = {
                int(k): int(v) if v is not None else 0 for k, v in participants.items()
            }
        else:
            # assume list
            result_participants = {int(participant): 0 for participant in participants}

        result = None

        # Генерируем нужный список в зависимости от типа чата
        if type == "DIALOG":
            result = {
                "id": id,
                "type": type,
                "status": "ACTIVE",
                "owner": owner,
                "participants": result_participants,
                "lastMessage": lastMessage,
                "lastEventTime": lastEventTime,
                "lastDelayedUpdateTime": 0,
                "lastFireDelayedErrorTime": 0,
                "created": 1,
                "cid": id,
                "prevMessageId": prevMessageId,
                "joinTime": 1,
                "modified": lastEventTime,
            }

        # Возвращаем
        return result

    async def generate_chats(
        self,
        chatIds,
        db_pool,
        senderId,
        include_favourites=True,
        protocol_type="mobile",
    ):
        """Генерирует чаты для отдачи клиенту"""
        # Готовый список с чатами
        chats = []

        # Формируем список чатов
        for chatId in chatIds:
            async with db_pool.acquire() as db_connection:
                async with db_connection.cursor() as cursor:
                    # Получаем чат по id
                    await cursor.execute(
                        "SELECT * FROM `chats` WHERE id = %s", (chatId,)
                    )
                    row = await cursor.fetchone()

                    if row:
                        # Получаем последнее сообщение из чата
                        message, messageTime = await self.get_last_message(
                            chatId, db_pool, protocol_type=protocol_type
                        )

                        # Формируем список участников с временем последней активности
                        participant_ids = await self.get_chat_participants(
                            chatId, db_pool
                        )

                        participants = await self.get_participant_last_activity(
                            chatId, participant_ids, db_pool
                        )

                        # Получаем ID предыдущего сообщения
                        prevMessageId = await self.get_previous_message_id(
                            chatId, db_pool, protocol_type=protocol_type
                        )

                        # Выносим результат в лист
                        chats.append(
                            self.generate_chat(
                                row.get("id"),
                                row.get("owner"),
                                row.get("type"),
                                participants,
                                message,
                                messageTime,
                                prevMessageId,
                            )
                        )

        if include_favourites:
            # Получаем последнее сообщение из избранного
            message, messageTime = await self.get_last_message(
                senderId, db_pool, protocol_type=protocol_type
            )

            # ID избранного
            chatId = senderId ^ senderId

            # Получаем последнюю активность участника (отправителя) в избранном
            participants = await self.get_participant_last_activity(
                senderId, [senderId], db_pool
            )

            # Получаем ID предыдущего сообщения для избранного (чат ID = senderId)
            prevMessageId = await self.get_previous_message_id(
                senderId, db_pool, protocol_type=protocol_type
            )

            # Хардкодим в лист чатов избранное
            chats.append(
                self.generate_chat(
                    chatId if protocol_type == "mobile" else str(chatId),
                    senderId,
                    "DIALOG",
                    participants,
                    message,
                    messageTime,
                    prevMessageId,
                )
            )

        return chats

    async def insert_message(
        self, chatId, senderId, text, attaches, elements, cid, type, db_pool
    ):
        """Добавление сообщения в историю"""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                # Получаем id последнего сообщения в чате
                await cursor.execute(
                    "SELECT id FROM `messages` WHERE chat_id = %s ORDER BY time DESC LIMIT 1",
                    (chatId,),
                )

                row = await cursor.fetchone() or {}
                last_message_id = row.get("id") or 0  # последнее id сообщения в чате
                message_id = self.generate_id()
                message_time = int(time.time() * 1000)  # время отправки сообщения

                # Вносим новое сообщение в таблицу
                await cursor.execute(
                    "INSERT INTO `messages` (id, chat_id, sender, time, text, attaches, cid, elements, type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        message_id,
                        chatId,
                        senderId,
                        message_time,
                        text,
                        json.dumps(attaches),
                        cid,
                        json.dumps(elements),
                        type,
                    ),
                )

        # Возвращаем айдишки
        return int(message_id), int(last_message_id), message_time

    async def get_last_message(self, chatId, db_pool, protocol_type="mobile"):
        """Получение последнего сообщения в чате"""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                # Получаем id последнего сообщения в чате
                await cursor.execute(
                    "SELECT * FROM `messages` WHERE chat_id = %s ORDER BY time DESC LIMIT 1",
                    (chatId,),
                )

                row = await cursor.fetchone()

                # Если нет результатов - возвращаем None
                if not row:
                    return None, None

                # Собираем сообщение
                message = {
                    "id": row.get("id")
                    if protocol_type == "mobile"
                    else str(row.get("id")),
                    "time": int(row.get("time")),
                    "type": row.get("type"),
                    "sender": row.get("sender"),
                    "cid": int(row.get("cid")),
                    "text": row.get("text"),
                    "attaches": json.loads(row.get("attaches")),
                    "elements": json.loads(row.get("elements")),
                    "reactionInfo": {},
                }

                # Возвращаем
                return message, int(row.get("time"))

    async def get_previous_message_id(self, chatId, db_pool, protocol_type="mobile"):
        """Получение ID предыдущего сообщения (второго с конца) в чате."""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT id FROM `messages` WHERE chat_id = %s ORDER BY time DESC LIMIT 1 OFFSET 1",
                    (chatId,),
                )
                row = await cursor.fetchone()

                # Если результат есть, возвращаем его
                if row:
                    return (
                        row.get("id")
                        if protocol_type == "mobile"
                        else str(row.get("id"))
                    )

                # В ином случае возвращаем 0
                return 0 if protocol_type == "mobile" else "0"

    async def get_participant_last_activity(self, chatId, participant_ids, db_pool):
        """Возвращает словарь {participant_id: last_activity_time} для участников чата."""
        if not participant_ids:
            return {}

        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                # Собираем всех участников
                placeholders = ",".join(["%s"] * len(participant_ids))
                query = f"""
                    SELECT sender, MAX(time) as last_time
                    FROM messages
                    WHERE chat_id = %s AND sender IN ({placeholders})
                    GROUP BY sender
                """
                params = (chatId,) + tuple(participant_ids)
                await cursor.execute(query, params)
                rows = await cursor.fetchall()

                # Собираем список участников без времени последней активности в чате
                result = {int(pid): 0 for pid in participant_ids}

                # Обновляем для каждого участника время последней активности в чате
                for row in rows:
                    sender = int(row["sender"])
                    last_time = row["last_time"]
                    if last_time is not None:
                        result[sender] = int(last_time)

                return result

    async def get_chat_participants(self, chatId, db_pool):
        """Возвращает список ID участников чата из таблицы chat_participants."""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT user_id FROM chat_participants WHERE chat_id = %s",
                    (chatId,),
                )
                rows = await cursor.fetchall()
                return [int(row["user_id"]) for row in rows]

    async def auth_required(self, userPhone, coro, *args):
        if userPhone:
            await coro(*args)

    def generate_id(self):
        # Получаем время в юниксе
        timestamp = int(time.time())

        # Генерируем дополнительно рандомное число
        random_number = random.randint(0, 9999)

        # Собираем их вместе и вычисляем хеш
        combined = f"{timestamp}{random_number}".encode()
        unique_id = int(hashlib.md5(combined).hexdigest(), 16) % 1000000000

        # Возвращаем
        return unique_id
