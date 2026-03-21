"""对账模型 - 平台账单对账"""

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


class StatementType(str, enum.Enum):
    """账单类型"""
    SETTLEMENT = "settlement"     # 结算账单
    COMMISSION = "commission"     # 佣金账单
    PROMOTION = "promotion"       # 推广费账单
    REFUND = "refund"             # 退款账单
    SERVICE_FEE = "service_fee"   # 服务费账单


class ReconciliationStatus(str, enum.Enum):
    """对账状态"""
    PENDING = "pending"           # 待对账
    MATCHED = "matched"           # 已匹配
    DISCREPANCY = "discrepancy"   # 有差异
    RESOLVED = "resolved"         # 差异已处理
    IGNORED = "ignored"           # 已忽略


class PlatformStatement(Base):
    """平台账单（从平台下载的结算/佣金等账单）"""
    __tablename__ = "platform_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), comment="平台ID")
    statement_type: Mapped[StatementType] = mapped_column(
        Enum(StatementType), comment="账单类型"
    )
    statement_period_start: Mapped[date] = mapped_column(Date, comment="账单期间开始")
    statement_period_end: Mapped[date] = mapped_column(Date, comment="账单期间结束")

    # 账单金额汇总
    total_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="订单总额"
    )
    total_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="退款总额"
    )
    total_commission: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="佣金总额"
    )
    total_tech_service_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="技术服务费"
    )
    total_promotion_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="推广费总额"
    )
    total_settlement: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="结算金额"
    )

    file_name: Mapped[str | None] = mapped_column(String(255), comment="源文件名")
    import_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    records: Mapped[list["ReconciliationRecord"]] = relationship(
        back_populates="statement"
    )


class ReconciliationTask(Base):
    """对账任务"""
    __tablename__ = "reconciliation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), comment="平台ID")
    period_start: Mapped[date] = mapped_column(Date, comment="对账期间开始")
    period_end: Mapped[date] = mapped_column(Date, comment="对账期间结束")

    # 统计
    total_orders: Mapped[int] = mapped_column(Integer, default=0, comment="总订单数")
    matched_orders: Mapped[int] = mapped_column(Integer, default=0, comment="匹配订单数")
    discrepancy_orders: Mapped[int] = mapped_column(Integer, default=0, comment="差异订单数")
    discrepancy_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="差异总金额"
    )

    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="任务状态"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="完成时间")


class ReconciliationRecord(Base):
    """对账明细记录"""
    __tablename__ = "reconciliation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("reconciliation_tasks.id"), comment="任务ID"
    )
    statement_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform_statements.id"), comment="账单ID"
    )
    order_no: Mapped[str] = mapped_column(String(64), index=True, comment="订单编号")
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus), default=ReconciliationStatus.PENDING
    )

    # 系统记录金额（我方数据）
    system_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="系统金额"
    )
    system_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="系统佣金"
    )
    system_settlement: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="系统结算额"
    )

    # 平台账单金额（平台数据）
    platform_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台金额"
    )
    platform_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台佣金"
    )
    platform_settlement: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="平台结算额"
    )

    # 差异
    amount_diff: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="金额差异"
    )
    commission_diff: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="佣金差异"
    )
    settlement_diff: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="结算差异"
    )

    diff_reason: Mapped[str | None] = mapped_column(Text, comment="差异原因")
    resolution: Mapped[str | None] = mapped_column(Text, comment="处理方案")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, comment="处理时间")

    statement: Mapped["PlatformStatement | None"] = relationship(
        back_populates="records"
    )
