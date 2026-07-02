from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    corrected_text: Mapped[str] = mapped_column(Text, default="")
    summary_markdown: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[dict] = mapped_column(JSON, default=list)
    citations: Mapped[dict] = mapped_column(JSON, default=list)
    unused_block_ids: Mapped[dict] = mapped_column(JSON, default=list)