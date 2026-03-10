import json, time

class Tools:
    def __init__(self):
        pass

    def generate_profile(
        self, id=1, phone=70000000000, avatarUrl=None,
        photoId=None, updateTime=0,
        firstName="Test", lastName="Account", options=[], 
        description=None, accountStatus=0, profileOptions=[], 
        includeProfileOptions=True, username=None
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
                    "type": "ONEME"
                }
            ],
            "options": options,
            "accountStatus": accountStatus
        }


        if avatarUrl:
            contact["photoId"] = photoId
            contact["baseUrl"] = avatarUrl
            contact["baseRawUrl"] = avatarUrl

        if description:
            contact["description"] = description

        if username:
            contact["link"] = "https://max.ru/" + username

        if includeProfileOptions == True:
            return {
                "contact": contact,
                "profileOptions": profileOptions
            }
        else:
            return contact
        
    def generate_profile_tt(
        self, id=1, phone=70000000000, avatarUrl=None,
        photoId=None, updateTime=0,
        firstName="Test", lastName="Account", options=[], 
        description=None, username=None
    ):
        contact = {
            "id": id,
            "updateTime": updateTime,
            "phone": phone,
            "names": [
                {
                    "name": f"{firstName} {lastName}",
                    "type": "TT"
                }
            ],
            "options": options
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
           
    def generate_chat(self, id, owner, type, participants, lastMessage, lastEventTime):
        """Генерация чата"""
        # Генерируем список участников
        result_participants = {
            str(participant): 0 for participant in participants
        }

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
                "joinTime": 1,
                "modified": lastEventTime
            }

        # Возвращаем
        return result

    async def generate_chats(self, chatIds, db_pool, senderId):
        """Генерирует чаты для отдачи клиенту"""
        # Готовый список с чатами
        chats = []

        # Формируем список чатов
        for chatId in chatIds:
            async with db_pool.acquire() as db_connection:
                async with db_connection.cursor() as cursor:
                    # Получаем чат по id
                    await cursor.execute("SELECT * FROM `chats` WHERE id = %s", (chatId,))
                    row = await cursor.fetchone()

                    if row:
                        # Получаем последнее сообщение из чата
                        message, messageTime = await self.get_last_message(
                            chatId, db_pool
                        )

                        # Формируем список участников
                        participants = {
                            str(participant): 0 for participant in row.get("participants")
                        }

                        # Выносим результат в лист
                        chats.append(
                            self.generate_chat(
                                row.get("id"),
                                row.get("owner"),
                                row.get("type"),
                                participants,
                                message,
                                messageTime
                            )
                        )

        # Получаем последнее сообщение из избранного
        message, messageTime = await self.get_last_message(
            senderId, db_pool
        )

        # ID избранного
        chatId = senderId ^ senderId

        # Хардкодим в лист чатов избранное
        chats.append(
            self.generate_chat(
                chatId,
                senderId,
                "DIALOG",
                [senderId],
                message,
                messageTime
            )
        )

        return chats

    async def insert_message(self, chatId, senderId, text, attaches, elements, cid, type, db_pool):
        """Добавление сообщения в историю"""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                # Получаем id последнего сообщения в чате
                await cursor.execute("SELECT id FROM `messages` WHERE chat_id = %s ORDER BY time DESC LIMIT 1", (chatId,))

                row = await cursor.fetchone() or {}
                last_message_id = row.get("id") or 0 # последнее id сообщения в чате

                # Вносим новое сообщение в таблицу
                await cursor.execute(
                    "INSERT INTO `messages` (chat_id, sender, time, text, attaches, cid, elements, type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (chatId, senderId, int(time.time() * 1000), text, json.dumps(attaches), cid, json.dumps(elements), type)
                )

                message_id = cursor.lastrowid # id сообщения

        # Возвращаем айдишки
        return int(message_id), int(last_message_id)

    async def get_last_message(self, chatId, db_pool):
        """Получение последнего сообщения в чате"""
        async with db_pool.acquire() as db_connection:
            async with db_connection.cursor() as cursor:
                # Получаем id последнего сообщения в чате
                await cursor.execute("SELECT * FROM `messages` WHERE chat_id = %s ORDER BY time DESC LIMIT 1", (chatId,))

                row = await cursor.fetchone()
                
                # Если нет результатов - возвращаем None
                if not row:
                    return None, None

                # Собираем сообщение
                message = {
                    "id": row.get("id"),
                    "time": int(row.get("time")),
                    "type": row.get("type"),
                    "sender": row.get("sender"),
                    "cid": int(row.get("cid")),
                    "text": row.get("text"),
                    "attaches": json.loads(row.get("attaches")),
                    "elements": json.loads(row.get("elements")),
                    "reactionInfo": {}
                }

                # Возвращаем
                return message, int(row.get("time"))

    async def auth_required(self, userPhone, coro, *args):
        if userPhone:
            await coro(*args)
