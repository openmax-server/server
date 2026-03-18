import lz4.block, msgpack, logging, json

class Proto:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # TODO узнать какие должны быть лимиты и поменять,
    # сейчас это больше заглушка
    MAX_PAYLOAD_SIZE = 1048576 # 1 MB
    MAX_DECOMPRESSED_SIZE = 1048576 # 1 MB
    HEADER_SIZE = 10 # 1+2+1+2+4

    ### Работа с протоколом
    def unpack_packet(self, data: bytes) -> dict | None:
        # Проверяем минимальный размер пакета
        if len(data) < self.HEADER_SIZE:
            self.logger.warning(f"Пакет слишком маленький: {len(data)} байт")
            return None

        # Распаковываем заголовок
        ver = int.from_bytes(data[0:1], "big")
        cmd = int.from_bytes(data[1:3], "big")
        seq = int.from_bytes(data[3:4], "big")
        opcode = int.from_bytes(data[4:6], "big")
        packed_len = int.from_bytes(data[6:10], "big")

        # Флаг упаковки
        comp_flag = packed_len >> 24

        # Парсим данные пакета
        payload_length = packed_len & 0xFFFFFF

        # Проверяем размер payload
        if payload_length > self.MAX_PAYLOAD_SIZE:
            self.logger.warning(f"Payload слишком большой: {payload_length} B (лимит {self.MAX_PAYLOAD_SIZE})")
            return None

        # Проверяем длину пакета
        if len(data) < self.HEADER_SIZE + payload_length:
            self.logger.warning(f"Пакет неполный: требуется {self.HEADER_SIZE + payload_length} B, получено {len(data)}")
            return None

        payload_bytes = data[10 : 10 + payload_length]
        payload = None

        # Декодируем данные пакета
        if payload_bytes:
            # Разжимаем данные пакета, если требуется
            if comp_flag != 0:
                compressed_data = payload_bytes
                try:
                    payload_bytes = lz4.block.decompress(
                        compressed_data,
                        uncompressed_size=self.MAX_DECOMPRESSED_SIZE,
                    )
                except lz4.block.LZ4BlockError:
                    self.logger.warning("Ошибка декомпрессии LZ4")
                    return None

            # Распаковываем msgpack
            payload = msgpack.unpackb(payload_bytes, raw=False, strict_map_key=False)

        self.logger.debug(f"Распаковал - ver={ver} cmd={cmd} seq={seq} opcode={opcode} payload={payload}")

        # Возвращаем
        return {
            "ver": ver,
            "cmd": cmd,
            "seq": seq,
            "opcode": opcode,
            "payload": payload,
        }

    def pack_packet(self, ver: int = 10, cmd: int = 1, seq: int = 1, opcode: int = 6, payload: dict = None) -> bytes:
        # Запаковываем заголовок
        ver_b = ver.to_bytes(1, "big")
        cmd_b = cmd.to_bytes(2, "big")
        seq_b = seq.to_bytes(1, "big")
        opcode_b = opcode.to_bytes(2, "big")

        # Запаковываем данные пакета
        payload_bytes: bytes | None = msgpack.packb(payload)
        if payload_bytes is None:
            payload_bytes = b""
        payload_len = len(payload_bytes) & 0xFFFFFF
        payload_len_b = payload_len.to_bytes(4, 'big')

        self.logger.debug(f"Упаковал - ver={ver} cmd={cmd} seq={seq} opcode={opcode} payload={payload}")

        # Возвращаем пакет
        return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes
    
    ### Констаты протокола
    CMD_OK = 0x100
    CMD_NOF = 0x200
    CMD_ERR = 0x300
    PROTO_VER = 10

    HELLO = 6
    REQUEST_CODE = 17
    VERIFY_CODE = 18
    FINAL_AUTH = 23
    LOGIN = 19
    PING = 1
    TELEMETRY = 5
    GET_ASSETS = 27
    GET_CALL_HISTORY = 79
    SEND_MESSAGE = 64
    GET_FOLDERS = 272
    GET_SESSIONS = 96
    LOGOUT = 20
    SEARCH_CHATS = 48
    SEARCH_BY_PHONE = 46