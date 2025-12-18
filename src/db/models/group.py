from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, ProcessingStatus

if TYPE_CHECKING:
    from src.db.models.group import GroupProcessing
    from src.db.models.product import Product
    from src.db.models.vendor import Vendor


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("vendors.id"))
    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="groups")

    group_processing_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups_processing.id"))
    group_processing: Mapped[GroupProcessing] = relationship("GroupProcessing", back_populates="groups")

    products: Mapped[list[Product]] = relationship("Product", back_populates="group")
    group_products: Mapped[list[GroupProduct]] = relationship("GroupProduct", back_populates="group")

    def __repr__(self):
        return f"Group(id={self.id}, file_processing_id={self.file_processing_id})"


class GroupProduct(Base):
    __tablename__ = "group_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"))
    group: Mapped[Group] = relationship("Group", back_populates="group_products")

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    product: Mapped[Product] = relationship("Product", back_populates="group_products")

    def __repr__(self):
        return f"GroupProduct(id={self.id}, group_id={self.group_id}, product_id={self.product_id})"


class GroupProcessing(Base):
    __tablename__ = "groups_processing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    status: Mapped[ProcessingStatus] = mapped_column(Enum(ProcessingStatus))
    groups: Mapped[list[Group]] = relationship("Group", back_populates="group_processing")

    def __repr__(self):
        return f"GroupProcessing(id={self.id})"
