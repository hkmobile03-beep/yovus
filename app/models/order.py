"""订单模型 - 电商平台订单数据"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlatformType(str, enum.Enum):
    """电商平台类型"""
    TMALL = "tmall"           # 天猫
    TAOBAO = "taobao"         # 淘宝
    JD_SELF = "jd_self"       # 京东自营
    JD_POP = "jd_pop"         # 京东POP


class OrderStatus(str, enum.Enum):
    """订单状态"""
    PENDING = "pending"             # 待付款
    PAID = "paid"                   # 已付款
    SHIPPED = "shipped"             # 已发货
    DELIVERED = "delivered"         # 已签收
    COMPLETED = "completed"         # 已完成
    REFUNDING = "refunding"         # 退款中
    REFUNDED = "refunded"           # 已退款
    CANCELLED = "cancelled"         # 已取消


class Platform(Base):
    """电商平台店铺"""
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), comment="店铺名称")
    platform_type: Mapped[PlatformType] = mapped_column(
        Enum(PlatformType), comment="平台类型"
    )
    shop_id: Mapped[str] = mapped_column(String(100), unique=True, comment="店铺ID")
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), comment="默认佣金费率"
    )
    tech_service_fee_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0"), comment="技术服务费率"
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    orders: Mapped[list["Order"]] = relationship(back_populates="platform")


class Order(Base):
    """电商订单"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), comment="平台ID")
    order_no: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, comment="订单编号"
    )
    platform_order_no: Mapped[str] = mapped_column(
        String(64), index=True, comment="平台订单号"
    )
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), comment="订单状态")

    # 金额字段 - 使用Decimal确保财务精度
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), comment="订单总金额(含税)"
    )
    product_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), comment="商品金额"
    )
    freight_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="运费"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="优惠金额"
    )
    platform_discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台承担优惠"
    )
    merchant_discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="商家承担优惠"
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台佣金"
    )
    actual_payment: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), comment="买家实付金额"
    )
    settlement_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台结算金额"
    )

    # 退款相关
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="退款金额"
    )

    # 时间
    order_time: Mapped[datetime] = mapped_column(DateTime, comment="下单时间")
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, comment="付款时间")
    ship_time: Mapped[datetime | None] = mapped_column(DateTime, comment="发货时间")
    complete_time: Mapped[datetime | None] = mapped_column(DateTime, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 关系
    platform: Mapped["Platform"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    """订单商品明细"""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), comment="订单ID")
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), comment="商品ID"
    )
    sku_code: Mapped[str] = mapped_column(String(64), comment="SKU编码")
    product_name: Mapped[str] = mapped_column(String(500), comment="商品名称")
    quantity: Mapped[int] = mapped_column(Integer, comment="数量")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="单价")
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="小计")
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="成本单价"
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.13"), comment="增值税税率"
    )
    refund_quantity: Mapped[int] = mapped_column(
        Integer, default=0, comment="退款数量"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="退款金额"
    )

    order: Mapped["Order"] = relationship(back_populates="items")
