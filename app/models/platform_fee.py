"""平台费用发票匹配模型

平台收取的各类费用，对应是否有发票、发票类型，
决定了哪些可以抵扣增值税进项、哪些是无票支出。
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformFeeType(str, enum.Enum):
    """平台费用类型"""
    COMMISSION = "commission"                 # 佣金（扣点）
    TECH_SERVICE_FEE = "tech_service_fee"     # 技术服务费（年费）
    PROMOTION_ZHITONGCHE = "ztc"              # 直通车
    PROMOTION_ZUANSHI = "zuanshi"             # 钻石展位/引力魔方
    PROMOTION_WANXIANGTAI = "wanxiangtai"     # 万相台
    PROMOTION_JDKUAICHE = "jd_kuaiche"        # 京东快车
    PROMOTION_JDJINGXUAN = "jd_jingxuan"      # 京东京选
    DELIVERY_FEE = "delivery_fee"             # 配送费（京东自营物流）
    STORAGE_FEE = "storage_fee"               # 仓储费
    PENALTY = "penalty"                       # 罚款/扣款
    DEPOSIT = "deposit"                       # 保证金
    OTHER = "other"                           # 其他


class InvoiceStatus(str, enum.Enum):
    """发票状态"""
    HAS_SPECIAL = "has_special"     # 有专票（可抵扣进项税）
    HAS_GENERAL = "has_general"     # 有普票（不可抵扣，但有票据）
    NO_INVOICE = "no_invoice"       # 无票
    PENDING = "pending"             # 待取票


class PlatformFeeRecord(Base):
    """平台费用明细（含发票匹配状态）

    用于跟踪每一笔平台扣费：
    - 是否已取得发票
    - 发票类型（专票可抵扣/普票不可抵扣）
    - 无票费用归入哪个税务分类
    """
    __tablename__ = "platform_fee_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id"), comment="平台ID"
    )
    fee_type: Mapped[PlatformFeeType] = mapped_column(
        Enum(PlatformFeeType), comment="费用类型"
    )
    period: Mapped[str] = mapped_column(
        String(7), index=True, comment="归属期间(YYYY-MM)"
    )

    # 金额
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="费用金额(含税)")
    amount_ex_tax: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="不含税金额"
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="税额"
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.06"), comment="税率（服务类通常6%）"
    )

    # 发票匹配
    invoice_status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.PENDING, comment="发票状态"
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("vat_invoices.id"), comment="关联发票ID"
    )
    invoice_no: Mapped[str | None] = mapped_column(String(32), comment="发票号码")

    # 无票时的税务处理分类
    no_invoice_tax_category: Mapped[str | None] = mapped_column(
        String(100), comment="无票税务分类(如：佣金支出-无票/推广费-无票)"
    )

    # 关联信息
    settlement_no: Mapped[str | None] = mapped_column(
        String(64), comment="结算单号"
    )
    fee_date: Mapped[date] = mapped_column(Date, comment="费用发生日期")
    description: Mapped[str | None] = mapped_column(Text, comment="费用说明")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlatformFeeInvoiceRule(Base):
    """平台费用开票规则

    记录各平台各类费用的开票规律：
    - 淘宝佣金：按月开专票（6%服务费）
    - 直通车/钻展：按月开专票（6%广告费）
    - 京东佣金：按月开专票
    - 京东配送费：按月开专票
    """
    __tablename__ = "platform_fee_invoice_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id"), comment="平台ID"
    )
    fee_type: Mapped[PlatformFeeType] = mapped_column(
        Enum(PlatformFeeType), comment="费用类型"
    )

    # 开票规则
    typical_invoice_type: Mapped[str] = mapped_column(
        String(20), default="special",
        comment="通常发票类型(special专票/general普票/none无票)"
    )
    typical_tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.06"), comment="通常税率"
    )
    invoice_cycle: Mapped[str] = mapped_column(
        String(20), default="monthly", comment="开票周期(monthly/quarterly)"
    )
    tax_category_code: Mapped[str | None] = mapped_column(
        String(32), comment="税收分类编码"
    )
    tax_category_name: Mapped[str | None] = mapped_column(
        String(100), comment="税收分类名称(如：信息技术服务/广告服务)"
    )
    can_deduct: Mapped[bool] = mapped_column(
        default=True, comment="是否可抵扣进项税"
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
