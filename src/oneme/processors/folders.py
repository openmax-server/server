import pydantic
import json
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import SyncFoldersPayloadModel, CreateFolderPayloadModel

class FoldersProcessors(BaseProcessor):
    async def folders_get(self, payload, seq, writer, senderPhone):
        """Синхронизация папок с сервером"""
        # Валидируем данные пакета
        try:
            SyncFoldersPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.FOLDERS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return
        
        # Ищем папки в бд
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, title, filters, `include`, options, update_time, source_id "
                    "FROM user_folders WHERE phone = %s ORDER BY sort_order",
                    (int(senderPhone),)
                )
                result_folders = await cursor.fetchall()

        folders = [
            {
                "id": folder["id"],
                "title": folder["title"],
                "filters": json.loads(folder["filters"]),
                "include": json.loads(folder["include"]),
                "updateTime": folder["update_time"],
                "options": json.loads(folder["options"]),
                "sourceId": folder["source_id"]
            }
            for folder in result_folders
        ]

        # Создаем данные пакета
        payload = {
            "folderSync": int(time.time() * 1000),
            "folders": folders,
            "foldersOrder": [folder["id"] for folder in result_folders],
            "allFilterExcludeFolders": []
        }

        # Собираем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.FOLDERS_GET, payload=payload
        )

        # Отправляем
        await self._send(writer, packet)

    async def folders_update(self, payload, seq, writer, senderPhone):
        """Создание папки"""
        # Валидируем данные пакета
        try:
            CreateFolderPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.FOLDERS_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return

        update_time = int(time.time() * 1000)

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) as max_order FROM user_folders WHERE phone = %s",
                    (int(senderPhone),)
                )
                row = await cursor.fetchone()
                next_order = row["max_order"] + 1

                # Создаем новую папку
                await cursor.execute(
                    "INSERT INTO user_folders (id, phone, title, filters, `include`, options, source_id, update_time, sort_order) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        payload.get("id"),
                        int(senderPhone),
                        payload.get("title"),
                        json.dumps(payload.get("filters")),
                        json.dumps(payload.get("include", [])),
                        json.dumps([]),
                        1,
                        update_time,
                        next_order,
                    )
                )
                await conn.commit()

                # Получаем обновленный порядок папок
                await cursor.execute(
                    "SELECT id FROM user_folders WHERE phone = %s ORDER BY sort_order",
                    (int(senderPhone),)
                )
                all_folders = await cursor.fetchall()

        folders_order = [f["id"] for f in all_folders]

        # Формируем данные пакета
        response_payload = {
            "folder": {
                "id": payload.get("id"),
                "title": payload.get("title"),
                "include": payload.get("include"),
                "filters": payload.get("filters"),
                "updateTime": update_time,
                "options": [],
                "sourceId": 1,
            },
            "folderSync": update_time,
            "foldersOrder": folders_order,
        }

        # Формируем пакет
        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.FOLDERS_UPDATE, payload=response_payload
        )

        await self._send(writer, packet)

        # Разработчики протокола, объяснитесь, что за хеш !!! а еще подарите нам способ его формирования
        notify_about_hash = self.proto.pack_packet(
            cmd=0, seq=1, opcode=self.opcodes.NOTIF_CONFIG,
            payload={"config": {"hash": "0"}}
        )

        await self._send(writer, notify_about_hash)