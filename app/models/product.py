"""商品模型"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductCategory(Base):
    """商品类目"""
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), comment="类目名称")
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_categories.id"), comment="父类目ID"
    )
    commission_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), comment="类目佣金费率"
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.13"), comment="增值税税率"
    )

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """商品"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, comment="SKU编码"
    )
    name: Mapped[str] = mapped_column(String(500), comment="商品名称")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_categories.id"), comment="类目ID"
    )

    # 价格与成本
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="销售价格")
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="采购成本")
    logistics_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="物流成本/件"
    )
    packaging_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="包装成本/件"
    )

    # 税务
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.13"), comment="增值税税率"
    )
    tax_category_code: Mapped[str | None] = mapped_column(
        String(32), comment="税收分类编码"
    )

    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    category: Mapped["ProductCategory | None"] = relationship(back_populates="products")
