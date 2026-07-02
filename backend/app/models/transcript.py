from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="transcript", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    speaker: Mapped[str] = mapped_column(String(50), default="")
    text: Mapped[str] = mapped_column(Text, default="")

    transcript: Mapped["Transcript"] = relationship(back_populates="segments")