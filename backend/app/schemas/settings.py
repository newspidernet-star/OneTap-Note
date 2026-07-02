from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    value: str
    is_required: bool = True


class SettingOut(BaseModel):
    key: str
    is_set: bool
    is_required: bool


class SettingsUpdate(BaseModel):
    settings: list[SettingItem]


class TestResult(BaseModel):
    key: str
    ok: bool
    message: str = ""