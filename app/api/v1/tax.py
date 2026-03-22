"""税务申报API"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.tax import TaxSummary, VATCalculation
from app.services.tax_service import TaxService

router = APIRouter()


@router.get("/vat/{period}", response_model=VATCalculation)
async def calculate_vat(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """计算增值税

    Args:
        period: 申报期间，格式 YYYY-MM，如 2026-03
    """
    service = TaxService(db)
    return await service.calculate_vat(period)


@router.get("/summary/{period}", response_model=TaxSummary)
async def get_tax_summary(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取税务汇总（增值税+附加税）"""
    service = TaxService(db)
    vat = await service.calculate_vat(period)
    surcharges = await service.calculate_surcharges(vat["tax_payable"])

    total_burden = (
        vat["tax_payable"] + surcharges["total_surcharges"]
    )

    return TaxSummary(
        period=period,
        vat=VATCalculation(**vat),
        surcharges=surcharges,
        total_tax_burden=total_burden,
    )


@router.post("/corporate-income-tax")
async def calculate_income_tax(
    period: str = Query(..., description="期间 YYYY-MM"),
    total_revenue: Decimal = Query(..., description="收入总额"),
    total_cost: Decimal = Query(..., description="成本总额"),
    total_expense: Decimal = Query(..., description="费用总额"),
    prior_losses: Decimal = Query(default=Decimal("0"), description="以前年度亏损"),
    db: AsyncSession = Depends(get_db),
):
    """计算企业所得税（季度预缴）"""
    service = TaxService(db)
    result = await service.calculate_corporate_income_tax(
        period=period,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_expense=total_expense,
        prior_losses=prior_losses,
    )
    return result


@router.post("/declaration/{period}")
async def generate_declaration(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """生成增值税纳税申报表"""
    service = TaxService(db)
    declaration = await service.generate_vat_declaration(period)
    return {
        "declaration_id": declaration.id,
        "period": period,
        "tax_due": declaration.tax_due,
        "message": "申报表已生成",
    }
