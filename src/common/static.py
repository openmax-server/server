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

    class ChatTypes:
        DIALOG = "DIALOG"

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
        }
    }

    COMPLAIN_REASONS = [
        # TODO: Было бы очень замечательно заполнить этот лист причинами для жалоб
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