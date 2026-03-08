import pydantic

class UserAgentModel(pydantic.BaseModel):
    deviceType: str
    appVersion: str
    osVersion: str
    timezone: str
    screen: str
    pushDeviceType: str
    locale: str
    deviceName: str
    deviceLocale: str

class HelloPayloadModel(pydantic.BaseModel):
    userAgent: UserAgentModel
    deviceId: str

class RequestCodePayloadModel(pydantic.BaseModel):
    phone: str

class VerifyCodePayloadModel(pydantic.BaseModel):
    verifyCode: str
    authTokenType: str
    token: str

class FinalAuthPayloadModel(pydantic.BaseModel):
    deviceType: str
    tokenType: str
    deviceId: str
    token: str