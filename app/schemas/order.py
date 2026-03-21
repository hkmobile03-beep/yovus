"""订单相关Schema"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PlatformCreate(BaseModel):
    name: str = Field(..., description="店铺名称")
    platform_type: str = Field(..., description="平台类型: tmall/taobao/jd_self/jd_pop")
    shop_id: str = Field(..., description="店铺ID")
    commission_rate: Decimal = Field(..., description="默认佣金费率")
    tech_service_fee_rate: Decimal = Field(default=Decimal("0"))
    remark: str | None = None


class PlatformResponse(PlatformCreate):
    id: int

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    sku_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    cost_price: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0.13")


class OrderCreate(BaseModel):
    platform_id: int
    order_no: str
    platform_order_no: str
    status: str = "paid"
    total_amount: Decimal
    product_amount: Decimal
    freight_amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    platform_discount: Decimal = Decimal("0")
    merchant_discount: Decimal = Decimal("0")
    actual_payment: Decimal
    order_time: datetime
    pay_time: datetime | None = None
    items: list[OrderItemCreate] = []


class OrderResponse(BaseModel):
    id: int
    platform_id: int
    order_no: str
    platform_order_no: str
    status: str
    total_amount: Decimal
    actual_payment: Decimal
    commission_amount: Decimal
    settlement_amount: Decimal
    refund_amount: Decimal
    order_time: datetime
    complete_time: datetime | None = None

    model_config = {"from_attributes": True}
