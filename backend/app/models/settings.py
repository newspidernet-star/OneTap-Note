from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiSettings(Base):
    __tablename__ = "api_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    encrypted_value: Mapped[str] = mapped_column(Text, default="")
    is_required: Mapped[bool] = mapped_column(default=True)