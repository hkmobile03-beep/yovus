"""对账相关Schema"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ReconciliationTaskCreate(BaseModel):
    platform_id: int
    period_start: date
    period_end: date


class ReconciliationTaskResponse(BaseModel):
    id: int
    platform_id: int
    period_start: date
    period_end: date
    total_orders: int
    matched_orders: int
    discrepancy_orders: int
    discrepancy_amount: Decimal
    status: str

    model_config = {"from_attributes": True}


class ReconciliationRecordResponse(BaseModel):
    id: int
    order_no: str
    status: str
    system_amount: Decimal
    system_commission: Decimal
    system_settlement: Decimal
    platform_amount: Decimal
    platform_commission: Decimal
    platform_settlement: Decimal
    amount_diff: Decimal
    commission_diff: Decimal
    settlement_diff: Decimal
    diff_reason: str | None = None

    model_config = {"from_attributes": True}


class ReconciliationSummary(BaseModel):
    total_records: int
    status_breakdown: dict[str, int]
    total_amount_diff: Decimal
    total_commission_diff: Decimal
    total_settlement_diff: Decimal
