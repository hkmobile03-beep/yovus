"""财务相关Schema"""

from decimal import Decimal

from pydantic import BaseModel


class PeriodSummary(BaseModel):
    period: str
    order_count: int
    total_revenue_ex_tax: Decimal
    total_cost: Decimal
    total_commission: Decimal
    total_refund: Decimal
    gross_profit: Decimal
    gross_margin: Decimal


class ProfitOverview(BaseModel):
    period: str
    order_count: int
    revenue: dict
    costs: dict
    profit: dict


class SKUProfit(BaseModel):
    sku_code: str
    product_name: str
    quantity: int
    revenue_ex_tax: Decimal
    cost_ex_tax: Decimal
    profit: Decimal
    margin: Decimal
    refund_amount: Decimal


class PlatformROI(BaseModel):
    platform_id: int
    platform_name: str
    platform_type: str
    order_count: int
    revenue: Decimal
    commission: Decimal
    promotion_cost: Decimal
    refund: Decimal
    total_cost: Decimal
    roi: Decimal
