from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str = "Untitled"
    client_id: str | None = None


class SessionNoteUpdate(BaseModel):
    user_note: str = ""


class SessionOut(BaseModel):
    id: int
    title: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    error_message: str | None = None
    client_id: str | None = None
    user_note: str = ""

    class Config:
        from_attributes = True


class MaterialOut(BaseModel):
    id: int
    type: str
    source: str
    sort_order: int
    status: str
    url: str | None = None
    original_url: str | None = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    material_id: int
    type: str
    status: str
