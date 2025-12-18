from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base


class File(Base):
    __tablename__ = "files"

    file_name: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str] = mapped_column(String(5))
    key: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def is_valid(self) -> bool:
        return self.uploaded_at is not None
