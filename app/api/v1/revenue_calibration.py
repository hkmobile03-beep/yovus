"""双口径收入对账 API

两种收入确认口径：
  1. 创建订单口径（你们的口径/ERP口径）= 当月创建订单 - 当月退款完成
  2. 确认收货口径（平台涉税推送口径）= 当月确认收货的订单金额

随时切换查看，方便和平台、税务局、ERP三方核对。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.revenue_calibration_service import (
    RevenueCalibration,
    RevenueCalibrationService,
)

router = APIRouter()


@router.get("/by-calibration")
async def get_revenue_by_calibration(
    year: int = Query(..., description="年份, 如 2026"),
    month: int = Query(..., description="月份, 如 3"),
    calibration: str = Query(
        ...,
        description="口径类型: order_creation(创建订单口径) 或 confirmed_receipt(确收口径)",
    ),
    platform_id: int | None = Query(None, description="平台ID，不填则汇总所有平台"),
    db: AsyncSession = Depends(get_db),
):
    """按指定口径查询收入

    示例：
    - /api/v1/revenue/by-calibration?year=2026&month=3&calibration=order_creation
    - /api/v1/revenue/by-calibration?year=2026&month=3&calibration=confirmed_receipt&platform_id=1
    """
    period_start, period_end = _build_period(year, month)

    service = RevenueCalibrationService(db)
    result = await service.calculate_revenue(
        platform_id=platform_id,
        period_start=period_start,
        period_end=period_end,
        calibration=RevenueCalibration(calibration),
    )
    return result


@router.get("/compare")
async def compare_calibrations(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份"),
    platform_id: int | None = Query(None, description="平台ID"),
    db: AsyncSession = Depends(get_db),
):
    """双口径对比分析

    同时输出两种口径的金额，以及差异明细：
    - 哪些订单只在口径一（本月创建但未确收）
    - 哪些订单只在口径二（非本月创建但本月确收）
    - 退款跨月导致的差异

    用于与平台涉税数据对账、与ERP数据核对。
    """
    period_start, period_end = _build_period(year, month)

    service = RevenueCalibrationService(db)
    return await service.compare_calibrations(
        platform_id=platform_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/multi-month-compare")
async def multi_month_compare(
    year: int = Query(..., description="年份"),
    start_month: int = Query(1, description="开始月份"),
    end_month: int = Query(12, description="结束月份"),
    platform_id: int | None = Query(None, description="平台ID"),
    db: AsyncSession = Depends(get_db),
):
    """多月份双口径对比

    输出指定年份多个月的双口径数据，方便看全年趋势和累计差异。
    """
    service = RevenueCalibrationService(db)
    results = []

    for m in range(start_month, end_month + 1):
        period_start, period_end = _build_period(year, m)
        comparison = await service.compare_calibrations(
            platform_id=platform_id,
            period_start=period_start,
            period_end=period_end,
        )
        results.append({
            "month": f"{year}-{str(m).zfill(2)}",
            "creation_net_inc_tax": comparison["creation_basis"]["net_amount_inc_tax"],
            "receipt_net_inc_tax": comparison["receipt_basis"]["net_amount_inc_tax"],
            "diff_inc_tax": comparison["difference"]["net_amount_inc_tax_diff"],
            "creation_net_ex_tax": comparison["creation_basis"]["net_amount_ex_tax"],
            "receipt_net_ex_tax": comparison["receipt_basis"]["net_amount_ex_tax"],
            "diff_ex_tax": comparison["difference"]["net_amount_ex_tax_diff"],
        })

    # 累计汇总
    from decimal import Decimal
    total_creation = sum((r["creation_net_inc_tax"] for r in results), Decimal("0"))
    total_receipt = sum((r["receipt_net_inc_tax"] for r in results), Decimal("0"))

    return {
        "year": year,
        "monthly_data": results,
        "cumulative": {
            "creation_total": total_creation,
            "receipt_total": total_receipt,
            "cumulative_diff": total_creation - total_receipt,
            "note": (
                "全年累计来看，两种口径的差异应趋近于零"
                "（除非年末有大量未确收订单或跨年退款），"
                "因为跨月的时间差最终会相互抵消。"
            ),
        },
    }


def _build_period(year: int, month: int) -> tuple[datetime, datetime]:
    """构建月度期间（精确到秒）"""
    import calendar

    _, last_day = calendar.monthrange(year, month)
    period_start = datetime(year, month, 1, 0, 0, 0)
    period_end = datetime(year, month, last_day, 23, 59, 59)
    return period_start, period_end
