"""预算预警相关Schema"""

from decimal import Decimal

from pydantic import BaseModel


class BudgetCreate(BaseModel):
    name: str
    budget_type: str
    year: int
    monthly_amounts: dict[str, Decimal]


class BudgetResponse(BaseModel):
    id: int
    name: str
    budget_type: str
    period: str
    budget_amount: Decimal
    actual_amount: Decimal
    variance: Decimal
    execution_rate: Decimal
    status: str

    model_config = {"from_attributes": True}


class BudgetExecution(BaseModel):
    period: str
    budgets: list[dict]
    total_budget: Decimal
    total_actual: Decimal
    total_variance: Decimal
    total_execution_rate: Decimal


class AlertRuleCreate(BaseModel):
    name: str
    description: str | None = None
    metric: str
    operator: str
    threshold_value: Decimal
    alert_level: str = "warning"


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    metric: str
    operator: str
    threshold_value: Decimal
    alert_level: str
    is_active: bool

    model_config = {"from_attributes": True}


class AlertLogResponse(BaseModel):
    id: int
    rule_id: int
    alert_level: str
    status: str
    title: str
    message: str
    metric_value: Decimal
    threshold_value: Decimal
    triggered_at: str

    model_config = {"from_attributes": True}
