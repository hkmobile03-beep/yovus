"""API v1路由"""

from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analytics,
    orders,
    reconciliation,
    tax,
)

router = APIRouter(prefix="/api/v1")

router.include_router(orders.router, prefix="/orders", tags=["订单管理"])
router.include_router(
    reconciliation.router, prefix="/reconciliation", tags=["对账管理"]
)
router.include_router(tax.router, prefix="/tax", tags=["税务申报"])
router.include_router(analytics.router, prefix="/analytics", tags=["利润分析"])
router.include_router(alerts.router, prefix="/alerts", tags=["预算预警"])
