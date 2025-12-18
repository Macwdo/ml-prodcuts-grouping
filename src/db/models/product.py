from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import settings
from src.db.models.base import Base, ProcessingStatus
from src.db.models.group import Group

if TYPE_CHECKING:
    from src.db.models.group import GroupProduct
    from src.db.models.vendor import Vendor


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(255), index=True, unique=True)

    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)

    group_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("groups.id"))
    group: Mapped[Group | None] = relationship("Group", back_populates="products")

    group_products: Mapped[list[GroupProduct]] = relationship("GroupProduct", back_populates="product")

    brand_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("product_brands.id"))
    brand: Mapped[ProductBrand | None] = relationship("ProductBrand", back_populates="products")

    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("product_categories.id"))
    category: Mapped[ProductCategory | None] = relationship("ProductCategory", back_populates="products")

    embedding: Mapped[VECTOR | None] = mapped_column(VECTOR(dim=settings.EMBEDDING_DIMENSION))

    vendor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("vendors.id"))
    vendor: Mapped[Vendor | None] = relationship("Vendor", back_populates="products")

    def __repr__(self):
        return f"Product(id={self.id}, name={self.name})"


class ProductProcessing(Base):
    __tablename__ = "product_processings"

    status: Mapped[ProcessingStatus] = mapped_column(Enum(ProcessingStatus))


class ProductBrand(Base):
    __tablename__ = "product_brands"

    normalized_name: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(255))

    products: Mapped[list[Product]] = relationship("Product", back_populates="brand")


class ProductCategory(Base):
    __tablename__ = "product_categories"

    normalized_name: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(255))

    products: Mapped[list[Product]] = relationship("Product", back_populates="category")
