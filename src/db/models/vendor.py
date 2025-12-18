from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base

if TYPE_CHECKING:
    from src.db.models.product import Group, Product


class Vendor(Base):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255))

    groups: Mapped[list[Group]] = relationship("Group", back_populates="vendor")
    products: Mapped[list[Product]] = relationship("Product", back_populates="vendor")
