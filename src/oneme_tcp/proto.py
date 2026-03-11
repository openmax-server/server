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

    ### Команды
    PING = 1
    DEBUG = 2
    RECONNECT = 3
    LOG = 5
    SESSION_INIT = 6
    PROFILE = 16
    AUTH_REQUEST = 17
    AUTH = 18
    LOGIN = 19
    LOGOUT = 20
    SYNC = 21
    CONFIG = 22
    AUTH_CONFIRM = 23
    AUTH_CREATE_TRACK = 112
    AUTH_CHECK_PASSWORD = 113
    AUTH_LOGIN_CHECK_PASSWORD = 115
    AUTH_LOGIN_PROFILE_DELETE = 116
    AUTH_LOGIN_RESTORE_PASSWORD = 101
    AUTH_VALIDATE_PASSWORD = 107
    AUTH_VALIDATE_HINT = 108
    AUTH_VERIFY_EMAIL = 109
    AUTH_CHECK_EMAIL = 110
    AUTH_SET_2FA = 111
    AUTH_2FA_DETAILS = 104
    ASSETS_GET = 26
    ASSETS_UPDATE = 27
    ASSETS_GET_BY_IDS = 28
    ASSETS_LIST_MODIFY = 261
    ASSETS_REMOVE = 259
    ASSETS_MOVE = 260
    ASSETS_ADD = 29
    PRESET_AVATARS = 25
    CONTACT_INFO = 32
    CONTACT_INFO_BY_PHONE = 46
    CONTACT_ADD = 33
    CONTACT_UPDATE = 34
    CONTACT_PRESENCE = 35
    CONTACT_LIST = 36
    CONTACT_SEARCH = 37
    CONTACT_MUTUAL = 38
    CONTACT_PHOTOS = 39
    CONTACT_SORT = 40
    CONTACT_VERIFY = 42
    REMOVE_CONTACT_PHOTO = 43
    CHAT_INFO = 48
    CHAT_HISTORY = 49
    CHAT_MARK = 50
    CHAT_MEDIA = 51
    CHAT_DELETE = 52
    CHATS_LIST = 53
    CHAT_CLEAR = 54
    CHAT_UPDATE = 55
    CHAT_CHECK_LINK = 56
    CHAT_JOIN = 57
    CHAT_LEAVE = 58
    CHAT_MEMBERS = 59
    PUBLIC_SEARCH = 60
    CHAT_PERSONAL_CONFIG = 61
    CHAT_CREATE = 63
    REACTIONS_SETTINGS_GET_BY_CHAT_ID = 258
    CHAT_REACTIONS_SETTINGS_SET = 257
    MSG_SEND = 64
    MSG_TYPING = 65
    MSG_DELETE = 66
    MSG_EDIT = 67
    MSG_DELETE_RANGE = 92
    MSG_REACTION = 178
    MSG_CANCEL_REACTION = 179
    MSG_GET_REACTIONS = 180
    MSG_GET_DETAILED_REACTIONS = 181
    CHAT_SEARCH = 68
    MSG_SHARE_PREVIEW = 70
    MSG_GET = 71
    MSG_SEARCH_TOUCH = 72
    MSG_SEARCH = 73
    MSG_GET_STAT = 74
    CHAT_SUBSCRIBE = 75
    VIDEO_CHAT_START = 76
    VIDEO_CHAT_START_ACTIVE = 78
    CHAT_MEMBERS_UPDATE = 77
    VIDEO_CHAT_HISTORY = 79
    PHOTO_UPLOAD = 80
    STICKER_UPLOAD = 81
    VIDEO_UPLOAD = 82
    VIDEO_PLAY = 83
    VIDEO_CHAT_CREATE_JOIN_LINK = 84
    CHAT_PIN_SET_VISIBILITY = 86
    FILE_UPLOAD = 87
    FILE_DOWNLOAD = 88
    LINK_INFO = 89
    SESSIONS_INFO = 96
    SESSIONS_CLOSE = 97
    PHONE_BIND_REQUEST = 98
    PHONE_BIND_CONFIRM = 99
    GET_INBOUND_CALLS = 103
    EXTERNAL_CALLBACK = 105
    OK_TOKEN = 158
    CHAT_COMPLAIN = 117
    MSG_SEND_CALLBACK = 118
    SUSPEND_BOT = 119
    LOCATION_STOP = 124
    GET_LAST_MENTIONS = 127
    STICKER_CREATE = 193
    STICKER_SUGGEST = 194
    VIDEO_CHAT_MEMBERS = 195
    NOTIF_MESSAGE = 128
    NOTIF_TYPING = 129
    NOTIF_MARK = 130
    NOTIF_CONTACT = 131
    NOTIF_PRESENCE = 132
    NOTIF_CONFIG = 134
    NOTIF_CHAT = 135
    NOTIF_ATTACH = 136
    NOTIF_CALL_START = 137
    NOTIF_CONTACT_SORT = 139
    NOTIF_MSG_DELETE_RANGE = 140
    NOTIF_MSG_DELETE = 142
    NOTIF_MSG_REACTIONS_CHANGED = 155
    NOTIF_MSG_YOU_REACTED = 156
    NOTIF_CALLBACK_ANSWER = 143
    CHAT_BOT_COMMANDS = 144
    BOT_INFO = 145
    NOTIF_LOCATION = 147
    NOTIF_LOCATION_REQUEST = 148
    NOTIF_ASSETS_UPDATE = 150
    NOTIF_DRAFT = 152
    NOTIF_DRAFT_DISCARD = 153
    DRAFT_SAVE = 176
    DRAFT_DISCARD = 177
    CHAT_HIDE = 196
    CHAT_SEARCH_COMMON_PARTICIPANTS = 198
    NOTIF_MSG_DELAYED = 154
    NOTIF_PROFILE = 159
    PROFILE_DELETE = 199
    PROFILE_DELETE_TIME = 200
    WEB_APP_INIT_DATA = 160
    COMPLAIN = 161
    COMPLAIN_REASONS_GET = 162
    FOLDERS_GET = 272
    FOLDERS_GET_BY_ID = 273
    FOLDERS_UPDATE = 274
    FOLDERS_REORDER = 275
    FOLDERS_DELETE = 276
    NOTIF_FOLDERS = 277

    AUTH_QR_APPROVE = 290
    NOTIF_BANNERS = 292
    CHAT_SUGGEST = 300
    AUDIO_PLAY = 301
    SEND_VOTE = 304
    VOTERS_LIST_BY_ANSWER = 305
    GET_POLL_UPDATES = 306