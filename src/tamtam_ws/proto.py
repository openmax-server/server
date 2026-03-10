import json

class Proto:
    def pack_packet(self, ver=10, cmd=1, seq=0, opcode=1, payload=None):
        # а разве не надо в жсон запаковывать ещё
        # о всё
        return json.dumps({
            "ver": ver,
            "cmd": cmd,
            "seq": seq,
            "opcode": opcode,
            "payload": payload
        })

    def unpack_packet(self, packet):
        # нужно try catch сделать
        # чтобы не сыпалось всё при неверных пакетах
        try:
            parsed_packet = json.loads(packet)
        except:
            return None
        
        return parsed_packet
        # мне кажется долго вручную всё писать
        # а как еще
        # ну вставить сюда целиком и потом через multiline cursor удалить лишнее
        # ну ты удалишь тогда. я на тачпаде
        # ладно щас другим способом удалю
        # всё нахуй
        # TAMTAM SOURCE LEAK 2026
        # так ну че делать будем 
        # так ну

        # 19 опкод сделан?
        # нет сэр пошли библиотеку тамы смотреть
        # мб найдем че. она без обфускации
        # а ты ее видишь?
        # пошли

    ### Констаты протокола
    CMD_OK = 1
    CMD_NOF = 2
    CMD_ERR = 3
    PROTO_VER = 10

    ### Команды
    PING = 1
    LOG = 5
    SESSION_INIT = 6
    PROFILE = 16
    AUTH_REQUEST = 17
    AUTH_CHECK_SCENARIO = 263
    AUTH = 18
    LOGIN = 19
    LOGOUT = 20
    SYNC = 21
    CONFIG = 22
    AUTH_CONFIRM = 23
    ASSETS_GET = 26
    ASSETS_UPDATE = 27
    ASSETS_GET_BY_IDS = 28
    ASSETS_ADD = 29
    ASSETS_REMOVE = 259
    ASSETS_MOVE = 260
    ASSETS_LIST_MODIFY = 261
    CONTACT_INFO = 32
    CONTACT_UPDATE = 34 
    CONTACT_PRESENCE = 35 
    CONTACT_LIST = 36 
    CONTACT_PHOTOS = 39 
    CONTACT_CREATE = 41 
    REMOVE_CONTACT_PHOTO = 43 
    OWN_CONTACT_SEARCH = 44 
    CHAT_INFO = 48 
    CHAT_HISTORY = 49 
    CHAT_MARK = 50 
    CHAT_MEDIA = 51 
    CHAT_DELETE = 52 
    CHAT_LIST = 53 
    CHAT_CLEAR = 54 
    CHAT_UPDATE = 55 
    CHAT_CHECK_LINK = 56 
    CHAT_JOIN = 57 
    CHAT_LEAVE = 58 
    CHAT_MEMBERS = 59 
    CHAT_CLOSE = 61 
    CHAT_BOT_COMMANDS = 144 
    CHAT_SUBSCRIBE = 75 
    PUBLIC_SEARCH = 60 
    CHAT_CREATE = 63 
    MSG_SEND = 64 
    MSG_TYPING = 65 
    MSG_DELETE = 66 
    MSG_EDIT = 67 
    CHAT_SEARCH = 68 
    MSG_SHARE_PREVIEW = 70 
    MSG_SEARCH_TOUCH = 72 
    MSG_SEARCH = 73 
    MSG_GET_STAT = 74 
    MSG_GET = 71 
    VIDEO_CHAT_START = 76 
    VIDEO_CHAT_JOIN = 102 
    VIDEO_CHAT_COMMAND = 78 
    VIDEO_CHAT_MEMBERS = 195 
    CHAT_MEMBERS_UPDATE = 77 
    PHOTO_UPLOAD = 80 
    STICKER_UPLOAD = 81 
    VIDEO_UPLOAD = 82 
    VIDEO_PLAY = 83 
    MUSIC_PLAY = 84 
    MUSIC_PLAY30 = 85 
    FILE_UPLOAD = 87 
    FILE_DOWNLOAD = 88 
    CHAT_PIN_SET_VISIBILITY = 86 
    LINK_INFO = 89 
    MESSAGE_LINK = 90 
    MSG_CONSTRUCT = 94 
    SESSIONS_INFO = 96 
    SESSIONS_CLOSE = 97 
    PHONE_BIND_REQUEST = 98 
    PHONE_BIND_CONFIRM = 99 
    UNBIND_OK_PROFILE = 100 
    CHAT_COMPLAIN = 117 
    MSG_SEND_CALLBACK = 118 
    SUSPEND_BOT = 119 
    MSG_REACT = 178 
    MSG_CANCEL_REACTION = 179 
    MSG_GET_REACTIONS = 180 
    MSG_GET_DETAILED_REACTIONS = 181 
    LOCATION_STOP = 124 
    LOCATION_SEND = 125 
    LOCATION_REQUEST = 126 
    NOTIF_MESSAGE = 128 
    NOTIF_TYPING = 129 
    NOTIF_MARK = 130 
    NOTIF_CONTACT = 131 
    NOTIF_PRESENCE = 132 
    NOTIF_CONFIG = 134 
    NOTIF_CHAT = 135 
    NOTIF_ATTACH = 136 
    NOTIF_VIDEO_CHAT_START = 137 
    NOTIF_VIDEO_CHAT_COMMAND = 138 
    NOTIF_CALLBACK_ANSWER = 143 
    NOTIF_MSG_CONSTRUCT = 146 
    NOTIF_LOCATION = 147 
    NOTIF_LOCATION_REQUEST = 148 
    NOTIF_ASSETS_UPDATE = 150 
    NOTIF_MSG_REACTIONS_CHANGED = 155 
    NOTIF_MSG_YOU_REACTED = 156 
    NOTIF_DRAFT = 152 
    NOTIF_DRAFT_DISCARD = 153 
    NOTIF_MSG_DELAYED = 154 
    AUTH_CALL_INFO = 256 
    CONTACT_INFO_EXTERNAL = 45 
    DRAFT_SAVE = 176 
    DRAFT_DISCARD = 177 
    STICKER_CREATE = 193 
    STICKER_SUGGEST = 194 
    CHAT_SEARCH_COUNT_MSG = 197 
    CHAT_SEARCH_COMMON_PARTICIPANTS = 198 
    GET_USER_SCORE = 201 