import pydantic
import json
import time
from classes.baseprocessor import BaseProcessor
from oneme.models import SyncFoldersPayloadModel

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
                    "SELECT id, title, filters, options, update_time, source_id "
                    "FROM user_folders WHERE phone = %s ORDER BY sort_order",
                    (int(senderPhone),)
                )
                result_folders = await cursor.fetchall()

        folders = [
            {
                "id": folder["id"],
                "title": folder["title"],
                "filters": json.loads(folder["filters"]),
                "updateTime": folder["update_time"],
                "options": json.loads(folder["options"]),
                "sourceId": folder["source_id"],
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