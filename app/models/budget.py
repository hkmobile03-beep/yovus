"""预算与预警模型"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BudgetType(str, enum.Enum):
    """预算类型"""
    REVENUE = "revenue"           # 收入预算
    COST = "cost"                 # 成本预算
    EXPENSE = "expense"           # 费用预算
    PROFIT = "profit"             # 利润预算
    CASH_FLOW = "cash_flow"       # 现金流预算


class AlertLevel(str, enum.Enum):
    """预警级别"""
    INFO = "info"           # 提示
    WARNING = "warning"     # 警告
    CRITICAL = "critical"   # 严重


class AlertStatus(str, enum.Enum):
    """预警状态"""
    ACTIVE = "active"       # 活跃
    ACKNOWLEDGED = "acknowledged"  # 已确认
    RESOLVED = "resolved"   # 已解决


class Budget(Base):
    """预算"""
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), comment="预算名称")
    budget_type: Mapped[BudgetType] = mapped_column(
        Enum(BudgetType), comment="预算类型"
    )
    period: Mapped[str] = mapped_column(String(7), index=True, comment="预算期间(YYYY-MM)")
    year: Mapped[int] = mapped_column(Integer, comment="预算年度")

    # 金额
    budget_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="预算金额"
    )
    actual_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="实际金额"
    )
    variance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="差异金额"
    )
    execution_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), default=Decimal("0"), comment="执行率"
    )

    status: Mapped[str] = mapped_column(
        String(20), default="active", comment="状态"
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    items: Mapped[list["BudgetItem"]] = relationship(back_populates="budget")


class BudgetItem(Base):
    """预算明细"""
    __tablename__ = "budget_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), comment="预算ID")
    category: Mapped[str] = mapped_column(String(100), comment="预算科目/分类")
    account_code: Mapped[str | None] = mapped_column(String(20), comment="关联会计科目")

    budget_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="预算金额"
    )
    actual_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="实际金额"
    )
    warning_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.80"), comment="预警阈值(80%)"
    )
    critical_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.95"), comment="严重阈值(95%)"
    )

    budget: Mapped["Budget"] = relationship(back_populates="items")


class AlertRule(Base):
    """预警规则"""
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), comment="规则名称")
    description: Mapped[str | None] = mapped_column(Text, comment="规则描述")

    # 规则配置
    metric: Mapped[str] = mapped_column(
        String(50), comment="监控指标(gross_margin/budget_rate/cash_flow/receivable_days)"
    )
    operator: Mapped[str] = mapped_column(
        String(10), comment="比较运算符(gt/lt/gte/lte/eq)"
    )
    threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), comment="阈值"
    )
    alert_level: Mapped[AlertLevel] = mapped_column(
        Enum(AlertLevel), comment="预警级别"
    )

    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AlertLog(Base):
    """预警日志"""
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), comment="规则ID")
    alert_level: Mapped[AlertLevel] = mapped_column(
        Enum(AlertLevel), comment="预警级别"
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus), default=AlertStatus.ACTIVE, comment="预警状态"
    )
    title: Mapped[str] = mapped_column(String(200), comment="预警标题")
    message: Mapped[str] = mapped_column(Text, comment="预警内容")
    metric_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), comment="触发时指标值"
    )
    threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), comment="阈值"
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, comment="确认时间")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, comment="解决时间")
