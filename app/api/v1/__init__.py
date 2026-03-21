"""API v1路由"""

from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analytics,
    orders,
    platform_fees,
    reconciliation,
    revenue_calibration,
    tax,
)

router = APIRouter(prefix="/api/v1")

router.include_router(orders.router, prefix="/orders", tags=["订单管理"])
router.include_router(
    reconciliation.router, prefix="/reconciliation", tags=["对账管理"]
)
router.include_router(
    revenue_calibration.router, prefix="/revenue", tags=["双口径收入对账"]
)
router.include_router(
    platform_fees.router, prefix="/platform-fees", tags=["平台费用与发票匹配"]
)
router.include_router(tax.router, prefix="/tax", tags=["税务申报"])
router.include_router(analytics.router, prefix="/analytics", tags=["利润分析"])
router.include_router(alerts.router, prefix="/alerts", tags=["预算预警"])
