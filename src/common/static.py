class Static:
    """Тут просто статические константы для их дальнейшего использования"""
    def __init__(self):
        pass

    class ErrorTypes:
        NOT_IMPLEMENTED = "not_implemented"
        INVALID_PAYLOAD = "invalid_payload"
        USER_NOT_FOUND = "user_not_found"
        CODE_EXPIRED = "code_expired"
        INVALID_CODE = "invalid_code"
        INVALID_TOKEN = "invalid_token"
        CHAT_NOT_FOUND = "chat_not_found"
        CHAT_NOT_ACCESS = "chat_not_access"
        RATE_LIMITED = "rate_limited"

    class ChatTypes:
        DIALOG = "DIALOG"

    class BotMessageTypes:
        WELCOME_ALREADY_REGISTERED = "welcome_already_registered"
        WELCOME_NEW_USER = "welcome_new_user"
        REGISTRATION_SUCCESS = "registration_success"
        ACCOUNT_ALREADY_EXISTS = "account_already_exists"
        ID_NOT_WHITELISTED = "id_not_whitelisted"
        INTERNAL_ERROR = "internal_error"
        INCOMING_CODE = "incoming_code"

    ERROR_TYPES = {
        "not_implemented": {
            "localizedMessage": "Не реализовано",
            "error": "proto.opcode",
            "message": "Not implemented",
            "title": "Не реализовано"
        },
        "invalid_payload": {
            "localizedMessage": "Ошибка валидации",
            "error": "proto.payload",
            "message": "Invalid payload",
            "title": "Ошибка валидации"
        },
        "user_not_found": {
            "localizedMessage": "Не нашли этот номер, проверьте цифры",
            "error": "error.phone.wrong",
            "message": "User not found",
            "title": "Не нашли этот номер, проверьте цифры"
        },
        "code_expired": {
            "localizedMessage": "Этот код устарел, запросите новый",
            "error": "error.code.expired",
            "message": "Code expired",
            "title": "Этот код устарел, запросите новый"
        },
        "invalid_code": {
            "localizedMessage": "Неверный код",
            "error": "error.code.wrong",
            "message": "Invalid code",
            "title": "Неверный код"
        },
        "invalid_token": {
            "localizedMessage": "Ошибка входа. Пожалуйста, авторизируйтесь снова",
            "error": "login.token",
            "message": "Invalid token",
            "title": "Ошибка входа. Пожалуйста, авторизируйтесь снова"
        },
        "chat_not_found": {
            "localizedMessage": "Чат не найден",
            "error": "chat.not.found",
            "message": "Chat not found",
            "title": "Чат не найден"
        },
        "chat_not_access": {
            "localizedMessage": "Нет доступа к чату",
            "error": "chat.not.access",
            "message": "Chat not access",
            "title": "Нет доступа к чату"
        },
        "rate_limited": {
            "localizedMessage": "Слишком много попыток. Повторите позже",
            "error": "error.rate_limited",
            "message": "Too many attempts. Please try again later",
            "title": "Слишком много попыток"
        }
    }

    ### Сообщения бота
    BOT_MESSAGES = {
        "welcome_already_registered": """
            👋 С возвращением в OpenMAX!
            Ваш номер, если забыли: {phone}
        """,
        "welcome_new_user": """
            👋 Добро пожаловать на этот инстанс OpenMAX!
            У вас ещё нет аккаунта. Используйте /register для создания.
        """,
        "registration_success": """
            ✅ Регистрация завершена!
            Ваш новый номер: {new_phone}
            Все коды для авторизации будут приходить сюда.
        """,
        "account_already_exists": """
            ❌ У вас уже есть аккаунт.
        """,
        "id_not_whitelisted": """
            ❌ Ваш ID не находится в белом списке.
        """,
        "internal_error": """
            ❌ Ошибка при регистрации аккаунта.
        """,
        "incoming_code": """
            Новая попытка входа в OpenMAX с вашим номером {phone}
            Код: {code}
            ❗️ Никому не сообщайте его, иначе можете потерять свой аккаунт!
        """
    }

    ### Причины для жалоб
    COMPLAIN_REASONS = [
        {"typeId": 5, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Мне не нравится", "reasonId": 22},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 4, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 3, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 7, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 8, "reasons": [
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Шантаж", "reasonId": 10},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 2, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Мне не нравится", "reasonId": 22},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 6, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
        {"typeId": 1, "reasons": [
            {"reasonTitle": "Мошенничество", "reasonId": 8},
            {"reasonTitle": "Спам", "reasonId": 9},
            {"reasonTitle": "Порнографический контент", "reasonId": 23},
            {"reasonTitle": "Насилие", "reasonId": 18},
            {"reasonTitle": "Оскорбления", "reasonId": 11},
            {"reasonTitle": "Экстремизм", "reasonId": 20},
            {"reasonTitle": "Запрещенные товары", "reasonId": 21},
            {"reasonTitle": "Другое", "reasonId": 7},
        ]},
    ]

    ### Заглушка для папок
    ALL_CHAT_FOLDER = [{
        "id": "all.chat.folder",
        "title": "Все",
        "filters": [],
        "updateTime": 0,
        "options": [],
        "sourceId": 1
    }]

    ALL_CHAT_FOLDER_ORDER = ["all.chat.folder"]

    ### Стандартные папки с настройками пользователя
    USER_FOLDERS = {
        "folders": [], 
        "foldersOrder": [], 
        "allFilterExcludeFolders": []
    }

    USER_SETTINGS = {
        "CHATS_PUSH_NOTIFICATION": "ON",
        "PUSH_DETAILS": True,
        "PUSH_SOUND": "DEFAULT",
        "INACTIVE_TTL": "6M",
        "CHATS_QUICK_REPLY": False,
        "SHOW_READ_MARK": True,
        "AUDIO_TRANSCRIPTION_ENABLED": True,
        "CHATS_LED": 65535,
        "SEARCH_BY_PHONE": "ALL",
        "INCOMING_CALL": "ALL",
        "DOUBLE_TAP_REACTION_DISABLED": False,
        "SAFE_MODE_NO_PIN": False,
        "CHATS_PUSH_SOUND": "DEFAULT",
        "DOUBLE_TAP_REACTION_VALUE": None,
        "FAMILY_PROTECTION": "OFF",
        "LED": 65535,
        "HIDDEN": False,
        "VIBR": True,
        "CHATS_INVITE": "ALL",
        "PUSH_NEW_CONTACTS": False,
        "UNSAFE_FILES": True,
        "DONT_DISTURB_UNTIL": 0,
        "CHATS_VIBR": True,
        "CONTENT_LEVEL_ACCESS": False,
        "STICKERS_SUGGEST": "ON",
        "SAFE_MODE": False,
        "M_CALL_PUSH_NOTIFICATION": "ON",
        "QUICK_REPLY": False
    }

    ### Коды стран, которым разрешён вход
    REG_COUNTRY_CODES = ['AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 
                         'AX', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 
                         'BO', 'BR', 'BS', 'BT', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 
                         'CK', 'CL', 'CM', 'CN', 'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 
                         'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 
                         'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 
                         'GQ', 'GR', 'GT', 'GU', 'GW', 'GY', 'HK', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 
                         'IM', 'IS', 'IN', 'IO', 'IQ', 'IR', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 
                         'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 
                         'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK', 'ML', 
                         'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 
                         'NA', 'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 
                         'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 
                         'RE', 'RO', 'RS', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SK', 
                         'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TG', 
                         'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 
                         'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'XK', 'YE', 
                         'YT', 'ZA', 'ZM', 'ZW']