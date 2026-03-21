"""预算与预警服务"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import (
    AlertLevel,
    AlertLog,
    AlertRule,
    AlertStatus,
    Budget,
    BudgetItem,
    BudgetType,
)


class BudgetService:
    """预算管理服务

    预算管理流程：
    1. 年度预算编制（按月分解）
    2. 月度预算执行跟踪
    3. 预算差异分析
    4. 预警规则检查
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_annual_budget(
        self,
        year: int,
        budget_type: BudgetType,
        monthly_amounts: dict[str, Decimal],
        name: str | None = None,
    ) -> list[Budget]:
        """创建年度预算（按月分解）

        Args:
            year: 预算年度
            budget_type: 预算类型
            monthly_amounts: 月度预算金额 {"01": 100000, "02": 120000, ...}
            name: 预算名称
        """
        budgets = []
        for month, amount in monthly_amounts.items():
            period = f"{year}-{month.zfill(2)}"
            budget = Budget(
                name=name or f"{year}年{month}月{budget_type.value}预算",
                budget_type=budget_type,
                period=period,
                year=year,
                budget_amount=amount,
            )
            self.db.add(budget)
            budgets.append(budget)

        return budgets

    async def update_actual_amount(
        self, budget_id: int, actual_amount: Decimal
    ) -> Budget:
        """更新预算实际执行金额"""
        result = await self.db.execute(
            select(Budget).where(Budget.id == budget_id)
        )
        budget = result.scalar_one()

        budget.actual_amount = actual_amount
        budget.variance = actual_amount - budget.budget_amount
        budget.execution_rate = (
            (actual_amount / budget.budget_amount * Decimal("100")).quantize(
                Decimal("0.01")
            )
            if budget.budget_amount > 0
            else Decimal("0")
        )

        return budget

    async def get_budget_execution(self, period: str) -> dict:
        """获取预算执行情况"""
        result = await self.db.execute(
            select(Budget).where(Budget.period == period)
        )
        budgets = result.scalars().all()

        summary = {
            "period": period,
            "budgets": [],
            "total_budget": Decimal("0"),
            "total_actual": Decimal("0"),
        }

        for b in budgets:
            summary["budgets"].append({
                "id": b.id,
                "name": b.name,
                "type": b.budget_type.value,
                "budget_amount": b.budget_amount,
                "actual_amount": b.actual_amount,
                "variance": b.variance,
                "execution_rate": b.execution_rate,
                "status": self._evaluate_budget_status(b),
            })
            summary["total_budget"] += b.budget_amount
            summary["total_actual"] += b.actual_amount

        summary["total_variance"] = (
            summary["total_actual"] - summary["total_budget"]
        )
        summary["total_execution_rate"] = (
            (
                summary["total_actual"]
                / summary["total_budget"]
                * Decimal("100")
            ).quantize(Decimal("0.01"))
            if summary["total_budget"] > 0
            else Decimal("0")
        )

        return summary

    async def check_alerts(self) -> list[AlertLog]:
        """检查所有预警规则并触发预警"""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.is_active == True)
        )
        rules = result.scalars().all()

        triggered = []
        for rule in rules:
            metric_value = await self._get_metric_value(rule.metric)
            if metric_value is None:
                continue

            should_alert = self._evaluate_rule(
                metric_value, rule.operator, rule.threshold_value
            )

            if should_alert:
                alert = AlertLog(
                    rule_id=rule.id,
                    alert_level=rule.alert_level,
                    title=f"预警：{rule.name}",
                    message=self._generate_alert_message(
                        rule, metric_value
                    ),
                    metric_value=metric_value,
                    threshold_value=rule.threshold_value,
                )
                self.db.add(alert)
                triggered.append(alert)

        return triggered

    async def create_alert_rule(
        self,
        name: str,
        metric: str,
        operator: str,
        threshold: Decimal,
        level: AlertLevel = AlertLevel.WARNING,
        description: str | None = None,
    ) -> AlertRule:
        """创建预警规则

        可监控指标：
        - gross_margin: 毛利率 (如 < 20% 告警)
        - budget_execution_rate: 预算执行率 (如 > 95% 告警)
        - refund_rate: 退款率 (如 > 5% 告警)
        - receivable_days: 应收账款周转天数 (如 > 30天 告警)
        - cash_balance: 现金余额 (如 < 50000 告警)
        - commission_rate_actual: 实际佣金费率 (如 > 8% 告警)
        """
        rule = AlertRule(
            name=name,
            description=description,
            metric=metric,
            operator=operator,
            threshold_value=threshold,
            alert_level=level,
        )
        self.db.add(rule)
        return rule

    async def acknowledge_alert(self, alert_id: int) -> AlertLog:
        """确认预警"""
        result = await self.db.execute(
            select(AlertLog).where(AlertLog.id == alert_id)
        )
        alert = result.scalar_one()
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        return alert

    async def _get_metric_value(self, metric: str) -> Decimal | None:
        """获取监控指标当前值（扩展点）"""
        # 这里需要根据不同指标从各服务获取数据
        # 目前返回None，后续接入实际数据
        return None

    @staticmethod
    def _evaluate_rule(
        value: Decimal, operator: str, threshold: Decimal
    ) -> bool:
        """评估规则是否触发"""
        ops = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
            "eq": value == threshold,
        }
        return ops.get(operator, False)

    @staticmethod
    def _evaluate_budget_status(budget: Budget) -> str:
        """评估预算执行状态"""
        if budget.budget_amount == 0:
            return "未设置"
        rate = budget.execution_rate
        if rate >= Decimal("95"):
            return "超支预警"
        elif rate >= Decimal("80"):
            return "接近预算"
        elif rate >= Decimal("50"):
            return "正常执行"
        else:
            return "执行偏低"

    @staticmethod
    def _generate_alert_message(
        rule: AlertRule, current_value: Decimal
    ) -> str:
        """生成预警消息"""
        op_text = {
            "gt": "超过",
            "lt": "低于",
            "gte": "达到或超过",
            "lte": "达到或低于",
            "eq": "等于",
        }
        return (
            f"指标[{rule.metric}]当前值为{current_value}，"
            f"已{op_text.get(rule.operator, '')}阈值{rule.threshold_value}。"
            f"预警级别：{rule.alert_level.value}"
        )
