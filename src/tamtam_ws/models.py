import pydantic

class MessageModel(pydantic.BaseModel):
    ver: int
    cmd: int
    seq: int
    opcode: int
    payload: dict = None

class UserAgentModel(pydantic.BaseModel):
    deviceType: str
    appVersion: str
    osVersion: str
    locale: str
    deviceLocale: str
    deviceName: str
    screen: str
    headerUserAgent: str
    timezone: str

class HelloPayloadModel(pydantic.BaseModel):
    userAgent: UserAgentModel
    deviceId: str

class RequestCodePayloadModel(pydantic.BaseModel):
    phone: str
    requestType: str
