from pydantic import BaseModel


class MatchResponse(BaseModel):
    pairs_count: int


class SummaryGenerateResponse(BaseModel):
    status: str


class KeyPointOut(BaseModel):
    point: str
    citations: list[str]


class SummaryResultOut(BaseModel):
    corrected_text: str
    summary: str
    key_points: list[KeyPointOut]
    corrections: list[dict]
    unused_block_ids: list[str]
    citation_valid: bool
    invalid_citations: list[str]


class VerificationOut(BaseModel):
    citation_valid: bool
    invalid_citations: list[str]
    unused_block_ids: list[str]
