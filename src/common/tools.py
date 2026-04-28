import json
import time
import os

import geoip2.database


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

        # для контактов, собственно
        custom_firstname=None,
        custom_lastname=None,

        blocked=False
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

        if custom_firstname:
            contact["names"].append(
                {
                    "name": custom_firstname,
                    "firstName": custom_firstname,
                    "lastName": custom_lastname,
                    "type": "CUSTOM"
                }
            )

        if blocked:
            contact["status"] = "BLOCKED"

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

    async def generate_contacts(
        self,
        contacts,
        db_pool,
        avatar_base_url="",
    ):
        """
            Генерация контакт-листа для отдачи клиенту
        
            [notes]
            В contacts должен поступать список вида

            [
                {
                    "firstname": "test",
                    "lastname": "testovich",
                    "id": 4323
                }
            ]

            А формировать мы должны его до вызова функции, 
            ибо я хочу вынести контакты в отдельную таблицу,
            по моему мнению так будет намного практичнее и лучше
        """
        # Готовый список с контакт-листом
        contact_list = []

        # Формируем список контактов
        for contact in contacts:
            # ID контакта
            contact_id = contact.get("id")

            # Имя и фамилия которые указал юзер для контакта
            firstname = contact.get("firstname")
            lastname = contact.get("lastname")
            blocked = contact.get("blocked", False)

            async with db_pool.acquire() as db_connection:
                async with db_connection.cursor() as cursor:
                    # Получаем контакт по id
                    await cursor.execute(
                        "SELECT * FROM `users` WHERE id = %s", (contact_id,)
                    )
                    user = await cursor.fetchone()

                    if user:
                        # Аватарка с биографией
                        photoId = (
                            None
                            if not user.get("avatar_id")
                            else int(user.get("avatar_id"))
                        )
                        avatar_url = (
                            None
                            if not photoId
                            else avatar_base_url + str(photoId)
                        )
                        description = (
                            None
                            if not user.get("description")
                            else user.get("description")
                        )

                        # Создаем профиль
                        contact = self.generate_profile(
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
                            includeProfileOptions=False,
                            username=user.get("username"),
                            custom_firstname=firstname,
                            custom_lastname=lastname,
                            blocked=blocked,
                        )

                        # Выносим результат в лист
                        contact_list.append(contact)

        return contact_list

    async def collect_user_contacts(
        self,
        owner_id,
        db_pool,
        avatar_base_url="",
    ):
        """Собирает все контакты пользователя и возвращает готовый контакт-лист"""
        contacts = []

        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM `contacts` WHERE owner_id = %s AND is_blocked = FALSE",
                    (owner_id,),
                )
                rows = await cursor.fetchall()

                for row in rows:
                    contacts.append(
                        {
                            "id": int(row.get("contact_id")),
                            "firstname": row.get("custom_firstname"),
                            "lastname": row.get("custom_lastname"),
                            "blocked": bool(row.get("is_blocked")),
                        }
                    )

        return await self.generate_contacts(
            contacts, db_pool, avatar_base_url=avatar_base_url
        )

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
                message_time = int(time.time() * 1000)  # время отправки сообщения

                # Вносим новое сообщение в таблицу
                await cursor.execute(
                    "INSERT INTO `messages` (chat_id, sender, time, text, attaches, cid, elements, type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
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

                message_id = cursor.lastrowid

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

    async def update_user_config(self, cursor, phone, user_settings, default_settings):
        """Функция для обновления юзер конфига из бд в случае его изменения"""

        user_config = json.loads(user_settings)
        updated_config = {**default_settings, **user_config}

        if updated_config != user_config:
            await cursor.execute(
                "UPDATE user_data SET user_config = %s WHERE phone = %s",
                (json.dumps(updated_config), phone),
            )

        return updated_config

    async def collect_presence(self, contact_ids, clients, db_pool):
        """Собирает статусы пользователей"""
        now = int(time.time())
        presence = {}

        # Список тех, кого нужно поискать в базе данных
        db_lookup_ids = []

        # Проходимся по всем айдишникам,
        # которые передал нам клиент
        for contact_id in contact_ids:
            contact_id = int(contact_id)

            client = clients.get(contact_id)

            # Если пользователь онлайн
            if client and client.get("status") == 2:
                presence[str(contact_id)] = {"seen": now, "status": 2}
            # Если пользователь подключен, 
            # но не взаимодействует с клиентом
            elif client and client.get("last_seen"):
                presence[str(contact_id)] = {"seen": client.get("last_seen")}
            # А если никакое условие не подошло, то добавляем его в лист,
            # а позже посмотрим в базе данных
            else:
                db_lookup_ids.append(contact_id)

        # Проходимся по листу и добавляем недостающих,
        # если такие существуют конечно
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for contact_id in db_lookup_ids:
                    await cursor.execute(
                        "SELECT lastseen FROM users WHERE id = %s",
                        (contact_id,)
                    )

                    row = await cursor.fetchone()
                    
                    if row:
                        lastseen = row.get("lastseen")
                        presence[int(contact_id)] = {"seen": int(lastseen)}

        return presence

    def get_geo(self, ip, db_path):
        """
            Получение страны пользователя по его айпи адресу
            Используется во время запуска сессии
        """
        try:
            with geoip2.database.Reader(db_path) as reader:
                response = reader.country(ip)
                return response.country.name or "Localhost Federation"
        except Exception: 
            return "Localhost Federation"