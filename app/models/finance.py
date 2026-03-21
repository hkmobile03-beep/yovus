"""财务核算模型 - 会计科目、凭证、成本"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
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


class AccountType(str, enum.Enum):
    """会计科目类型"""
    ASSET = "asset"               # 资产类
    LIABILITY = "liability"       # 负债类
    EQUITY = "equity"             # 所有者权益类
    REVENUE = "revenue"           # 收入类
    EXPENSE = "expense"           # 费用类
    COST = "cost"                 # 成本类


class VoucherType(str, enum.Enum):
    """凭证类型"""
    RECEIPT = "receipt"           # 收款凭证
    PAYMENT = "payment"           # 付款凭证
    TRANSFER = "transfer"         # 转账凭证
    GENERAL = "general"           # 通用记账凭证


class CostType(str, enum.Enum):
    """成本类型"""
    PURCHASE = "purchase"         # 采购成本
    LOGISTICS = "logistics"       # 物流成本
    PACKAGING = "packaging"       # 包装成本
    PLATFORM_FEE = "platform_fee" # 平台费用（佣金+技术服务费）
    PROMOTION = "promotion"       # 推广费用
    STORAGE = "storage"           # 仓储费用
    LABOR = "labor"               # 人工成本
    OTHER = "other"               # 其他成本


class Account(Base):
    """会计科目（按中国会计准则-小企业会计准则）"""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, comment="科目编码"
    )
    name: Mapped[str] = mapped_column(String(100), comment="科目名称")
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType), comment="科目类型"
    )
    parent_code: Mapped[str | None] = mapped_column(String(20), comment="上级科目编码")
    level: Mapped[int] = mapped_column(Integer, default=1, comment="科目层级")
    is_leaf: Mapped[bool] = mapped_column(default=True, comment="是否末级科目")
    balance_direction: Mapped[str] = mapped_column(
        String(10), default="debit", comment="余额方向(debit/credit)"
    )
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="期初余额"
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")


class AccountingVoucher(Base):
    """会计凭证"""
    __tablename__ = "accounting_vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voucher_no: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, comment="凭证编号"
    )
    voucher_type: Mapped[VoucherType] = mapped_column(
        Enum(VoucherType), comment="凭证类型"
    )
    voucher_date: Mapped[date] = mapped_column(Date, comment="凭证日期")
    period: Mapped[str] = mapped_column(String(7), comment="会计期间(YYYY-MM)")
    summary: Mapped[str] = mapped_column(String(500), comment="摘要")

    # 借贷合计（必须相等）
    total_debit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="借方合计"
    )
    total_credit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="贷方合计"
    )

    # 关联
    source_type: Mapped[str | None] = mapped_column(
        String(50), comment="来源类型(order/refund/settlement)"
    )
    source_id: Mapped[int | None] = mapped_column(Integer, comment="来源ID")

    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="状态(draft/posted/void)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过账时间")

    entries: Mapped[list["VoucherEntry"]] = relationship(back_populates="voucher")


class VoucherEntry(Base):
    """凭证分录"""
    __tablename__ = "voucher_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_vouchers.id"), comment="凭证ID"
    )
    account_code: Mapped[str] = mapped_column(String(20), comment="科目编码")
    account_name: Mapped[str] = mapped_column(String(100), comment="科目名称")
    summary: Mapped[str | None] = mapped_column(String(500), comment="分录摘要")
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="借方金额"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="贷方金额"
    )
    seq: Mapped[int] = mapped_column(Integer, default=0, comment="分录序号")

    voucher: Mapped["AccountingVoucher"] = relationship(back_populates="entries")


class CostRecord(Base):
    """成本记录"""
    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), comment="订单ID"
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), comment="商品ID"
    )
    cost_type: Mapped[CostType] = mapped_column(Enum(CostType), comment="成本类型")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="金额")
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="可抵扣税额"
    )
    period: Mapped[str] = mapped_column(String(7), comment="归属期间(YYYY-MM)")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
