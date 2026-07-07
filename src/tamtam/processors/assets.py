import pydantic
import time
from classes.baseprocessor import BaseProcessor
from tamtam.models import (
    AssetsPayloadModel,
    AssetsGetPayloadModel,
    AssetsGetByIdsPayloadModel,
    AssetsAddPayloadModel,
    AssetsRemovePayloadModel,
    AssetsMovePayloadModel,
    AssetsListModifyPayloadModel,
)

class AssetsProcessors(BaseProcessor):
    async def assets_update(self, payload, seq, writer):
        try:
            AssetsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_UPDATE, self.error_types.INVALID_PAYLOAD, writer)
            return

        response = {
            "sync": int(time.time() * 1000),
            "stickerSetsUpdates": {},
            "stickersUpdates": {},
            "stickersOrder": [
                "RECENT",
                "FAVORITE_STICKERS",
                "FAVORITE_STICKER_SETS",
                "TOP",
                "NEW",
                "NEW_STICKER_SETS",
            ],
            "sections": [
                {
                    "id": "RECENT",
                    "type": "RECENTS",
                    "recentsList": [],
                },
                {
                    "id": "FAVORITE_STICKERS",
                    "type": "STICKERS",
                    "stickers": [],
                    "marker": None,
                },
                {
                    "id": "FAVORITE_STICKER_SETS",
                    "type": "STICKER_SETS",
                    "stickerSets": [],
                    "marker": None,
                },
                {
                    "id": "TOP",
                    "type": "STICKERS",
                    "stickers": [],
                    "marker": None,
                },
                {
                    "id": "NEW",
                    "type": "STICKERS",
                    "stickers": [],
                    "marker": None,
                },
                {
                    "id": "NEW_STICKER_SETS",
                    "type": "STICKER_SETS",
                    "stickerSets": [],
                    "marker": None,
                },
            ],
        }

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_UPDATE, payload=response
        )
        await self._send(writer, packet)

    async def assets_get(self, payload, seq, writer):
        try:
            data = AssetsGetPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_GET, self.error_types.INVALID_PAYLOAD, writer)
            return

        asset_type = data.type
        if asset_type == "STICKER_SET":
            response = {"stickerSets": [], "marker": None}
        else:
            response = {"stickers": [], "marker": None}

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_GET, payload=response
        )
        await self._send(writer, packet)

    async def assets_get_by_ids(self, payload, seq, writer):
        try:
            data = AssetsGetByIdsPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_GET_BY_IDS, self.error_types.INVALID_PAYLOAD, writer)
            return

        asset_type = data.type
        if asset_type == "STICKER_SET":
            response = {"stickerSets": []}
        else:
            response = {"stickers": []}

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_GET_BY_IDS, payload=response
        )
        await self._send(writer, packet)

    async def assets_add(self, payload, seq, writer):
        try:
            AssetsAddPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_ADD, self.error_types.INVALID_PAYLOAD, writer)
            return

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_ADD, payload={}
        )
        await self._send(writer, packet)

    async def assets_remove(self, payload, seq, writer):
        try:
            AssetsRemovePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_REMOVE, self.error_types.INVALID_PAYLOAD, writer)
            return

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_REMOVE, payload={}
        )
        await self._send(writer, packet)

    async def assets_move(self, payload, seq, writer):
        try:
            AssetsMovePayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_MOVE, self.error_types.INVALID_PAYLOAD, writer)
            return

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_MOVE, payload={}
        )
        await self._send(writer, packet)

    async def assets_list_modify(self, payload, seq, writer):
        try:
            AssetsListModifyPayloadModel.model_validate(payload)
        except pydantic.ValidationError as error:
            self.logger.error(f"Возникли ошибки при валидации пакета: {error}")
            await self._send_error(seq, self.opcodes.ASSETS_LIST_MODIFY, self.error_types.INVALID_PAYLOAD, writer)
            return

        packet = self.proto.pack_packet(
            cmd=self.proto.CMD_OK, seq=seq, opcode=self.opcodes.ASSETS_LIST_MODIFY, payload={}
        )
        await self._send(writer, packet)
