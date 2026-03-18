import pydantic

class UserAgentModel(pydantic.BaseModel):
    deviceType: str
    appVersion: str
    osVersion: str
    timezone: str
    release: int = None
    screen: str
    pushDeviceType: str
    arch: str = None
    locale: str
    buildNumber: int
    deviceName: str
    deviceLocale: str

class HelloPayloadModel(pydantic.BaseModel):
    clientSessionId: int
    mt_instanceid: str = None
    userAgent: UserAgentModel
    deviceId: str

class RequestCodePayloadModel(pydantic.BaseModel):
    phone: str
    type: str

    @pydantic.field_validator('phone')
    def validate_phone(cls, v):
        """Валидация номера телефона"""
        if not v.replace("+", "").replace(" ", "").replace("-", "").isdigit():
            raise ValueError('phone must be digits')
        return v

    @pydantic.field_validator('type')
    def validate_type(cls, v):
        """Валидация типа запроса"""
        if not v in ("START_AUTH", "RESEND"):
            raise ValueError('type must be valid')
        return v
    
class VerifyCodePayloadModel(pydantic.BaseModel):
    verifyCode: str
    authTokenType: str
    token: str

class LoginPayloadModel(pydantic.BaseModel):
    interactive: bool
    token: str

class PingPayloadModel(pydantic.BaseModel):
    interactive: bool

class AssetsPayloadModel(pydantic.BaseModel):
    sync: int
    type: str

class GetCallHistoryPayloadModel(pydantic.BaseModel):
    forward: bool
    count: int

class MessageModel(pydantic.BaseModel):
    isLive: bool
    detectShare: bool
    elements: list
    attaches: list = None
    cid: int
    text: str = None

class SendMessagePayloadModel(pydantic.BaseModel):
    # TODO: пишем сервер макса в 2 ночи и не понимаем как это валидировать (блять)
    userId: int = None
    chatId: int = None
    message: MessageModel

class SyncFoldersPayloadModel(pydantic.BaseModel):
    folderSync: int

class SearchChatsPayloadModel(pydantic.BaseModel):
    chatIds: list

class SearchByPhonePayloadModel(pydantic.BaseModel):
    phone: str

class GetCallTokenPayloadModel(pydantic.BaseModel):
    userId: int
    value: str

class TypingPayloadModel(pydantic.BaseModel):
    chatId: int
    type: str = None

class SearchUsersPayloadModel(pydantic.BaseModel):
    contactIds: list

class ComplainReasonsGetPayloadModel(pydantic.BaseModel):
    complainSync: int

class UpdateProfilePayloadModel(pydantic.BaseModel):
    description: str = None
    firstName: str = None
    lastName: str = None

class AuthConfirmRegisterPayloadModel(pydantic.BaseModel):
    token: str
    firstName: str
    lastName: str = None
    tokenType: str

    @pydantic.field_validator('firstName')
    def validate_first_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('firstName must not be empty')
        if len(v) > 59:
            raise ValueError('firstName too long')
        return v

    @pydantic.field_validator('lastName')
    def validate_last_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 59:
            raise ValueError('lastName too long')
        return v

class ChatHistoryPayloadModel(pydantic.BaseModel):
    chatId: int
    backward: int