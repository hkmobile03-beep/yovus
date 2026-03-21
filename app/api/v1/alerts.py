"""预算预警API"""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.budget import AlertLevel, BudgetType
from app.schemas.budget import AlertRuleCreate, BudgetCreate
from app.services.budget_service import BudgetService

router = APIRouter()


@router.post("/budgets")
async def create_budget(
    data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建年度预算

    请求示例：
    {
        "name": "2026年收入预算",
        "budget_type": "revenue",
        "year": 2026,
        "monthly_amounts": {
            "01": 100000, "02": 80000, "03": 120000,
            "04": 110000, "05": 130000, "06": 150000,
            "07": 140000, "08": 160000, "09": 120000,
            "10": 100000, "11": 200000, "12": 250000
        }
    }
    """
    service = BudgetService(db)
    budgets = await service.create_annual_budget(
        year=data.year,
        budget_type=BudgetType(data.budget_type),
        monthly_amounts=data.monthly_amounts,
        name=data.name,
    )
    return {
        "message": f"已创建 {len(budgets)} 个月度预算",
        "year": data.year,
        "total_annual_budget": sum(
            b.budget_amount for b in budgets
        ),
    }


@router.get("/budgets/{period}")
async def get_budget_execution(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取预算执行情况"""
    service = BudgetService(db)
    return await service.get_budget_execution(period)


@router.put("/budgets/{budget_id}/actual")
async def update_budget_actual(
    budget_id: int,
    actual_amount: Decimal,
    db: AsyncSession = Depends(get_db),
):
    """更新预算实际执行金额"""
    service = BudgetService(db)
    budget = await service.update_actual_amount(budget_id, actual_amount)
    return {
        "budget_id": budget.id,
        "execution_rate": budget.execution_rate,
        "variance": budget.variance,
    }


@router.post("/rules")
async def create_alert_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建预警规则

    可用指标(metric)：
    - gross_margin: 毛利率
    - budget_execution_rate: 预算执行率
    - refund_rate: 退款率
    - receivable_days: 应收账款周转天数
    - cash_balance: 现金余额
    - commission_rate_actual: 实际佣金费率

    运算符(operator): gt, lt, gte, lte, eq
    """
    service = BudgetService(db)
    rule = await service.create_alert_rule(
        name=data.name,
        metric=data.metric,
        operator=data.operator,
        threshold=data.threshold_value,
        level=AlertLevel(data.alert_level),
        description=data.description,
    )
    return {"rule_id": rule.id, "message": "预警规则已创建"}


@router.post("/check")
async def check_alerts(
    db: AsyncSession = Depends(get_db),
):
    """执行预警检查"""
    service = BudgetService(db)
    triggered = await service.check_alerts()
    return {
        "triggered_count": len(triggered),
        "alerts": [
            {"title": a.title, "level": a.alert_level.value, "message": a.message}
            for a in triggered
        ],
    }


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """确认预警"""
    service = BudgetService(db)
    alert = await service.acknowledge_alert(alert_id)
    return {"alert_id": alert.id, "status": alert.status.value}
