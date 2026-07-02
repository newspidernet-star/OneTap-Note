from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled")
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[str] = mapped_column(String(50))
    updated_at: Mapped[str] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    materials: Mapped[list["Material"]] = relationship(back_populates="session")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    type: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(String(500))
    original_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    session: Mapped["Session"] = relationship(back_populates="materials")
    evidence_blocks: Mapped[list["EvidenceBlock"]] = relationship(back_populates="material")


class EvidenceBlock(Base):
    __tablename__ = "evidence_blocks"
    __table_args__ = (UniqueConstraint("session_id", "block_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_id: Mapped[str] = mapped_column(String(10))
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(10))
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)
    end_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    material: Mapped["Material"] = relationship(back_populates="evidence_blocks")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    speech_block_id: Mapped[int] = mapped_column(ForeignKey("evidence_blocks.id"))
    screen_block_id: Mapped[int] = mapped_column(ForeignKey("evidence_blocks.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    time_sim: Mapped[float] = mapped_column(Float, default=0.0)
    keyword_sim: Mapped[float] = mapped_column(Float, default=0.0)
    semantic_sim: Mapped[float] = mapped_column(Float, default=0.0)