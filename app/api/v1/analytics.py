"""利润分析API"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.accounting_service import AccountingService
from app.services.profit_service import ProfitService

router = APIRouter()


@router.get("/profit/{period}")
async def get_profit_overview(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取整体利润分析

    Args:
        period: 期间，格式 YYYY-MM
    """
    service = ProfitService(db)
    return await service.get_overall_profit(period)


@router.get("/sku-profit/{period}")
async def get_sku_profit(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取SKU级别利润分析"""
    service = ProfitService(db)
    return await service.get_sku_profit(period)


@router.get("/platform-roi/{period}")
async def get_platform_roi(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取各平台渠道ROI分析"""
    service = ProfitService(db)
    return await service.get_platform_roi(period)


@router.get("/period-summary/{period}")
async def get_period_summary(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取期间汇总数据"""
    service = AccountingService(db)
    return await service.get_period_summary(period)
