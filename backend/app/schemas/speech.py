from pydantic import BaseModel


class TranscriptionSegmentOut(BaseModel):
    start_time: float
    end_time: float
    speaker: str
    text: str


class TranscriptOut(BaseModel):
    session_id: int
    segments: list[TranscriptionSegmentOut]


class TranscribeResponse(BaseModel):
    task_id: str
    status: str
