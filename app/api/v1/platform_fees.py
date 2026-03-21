"""平台费用与发票匹配 API

管理平台收取的各类费用，跟踪发票取得情况：
- 有专票的费用 → 进项税可抵扣
- 有普票的费用 → 不可抵扣但有凭证
- 无票的费用 → 需要做纳税调增或其他税务处理
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.platform_fee import InvoiceStatus, PlatformFeeType
from app.services.platform_fee_service import PlatformFeeInvoiceService

router = APIRouter()


class PlatformFeeCreate(BaseModel):
    platform_id: int
    fee_type: str = Field(
        ...,
        description=(
            "费用类型: commission/tech_service_fee/ztc/zuanshi/"
            "wanxiangtai/jd_kuaiche/jd_jingxuan/delivery_fee/"
            "storage_fee/penalty/deposit/other"
        ),
    )
    amount: Decimal = Field(..., description="费用金额(含税)")
    fee_date: date
    period: str = Field(..., description="归属期间 YYYY-MM")
    description: str | None = None
    tax_rate: Decimal = Field(
        default=Decimal("0.06"), description="税率，服务类6%，运输9%"
    )


class InvoiceMatchRequest(BaseModel):
    fee_record_id: int
    invoice_id: int
    invoice_no: str
    invoice_status: str = Field(
        ..., description="has_special(专票) 或 has_general(普票)"
    )


class NoInvoiceMarkRequest(BaseModel):
    fee_record_id: int
    tax_category: str = Field(
        ...,
        description="税务分类，如'佣金支出-无票'、'推广费-无票'",
    )


@router.post("/record")
async def record_platform_fee(
    data: PlatformFeeCreate,
    db: AsyncSession = Depends(get_db),
):
    """记录平台费用"""
    service = PlatformFeeInvoiceService(db)
    record = await service.record_platform_fee(
        platform_id=data.platform_id,
        fee_type=PlatformFeeType(data.fee_type),
        amount=data.amount,
        fee_date=data.fee_date,
        period=data.period,
        description=data.description,
        tax_rate=data.tax_rate,
    )
    return {
        "id": record.id,
        "amount": data.amount,
        "amount_ex_tax": record.amount_ex_tax,
        "tax_amount": record.tax_amount,
        "message": "费用已记录，请及时匹配发票",
    }


@router.get("/summary/{period}")
async def get_fee_invoice_summary(
    period: str,
    platform_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取平台费用发票汇总

    输出分四组：
    1. 有专票（可抵扣进项税）
    2. 有普票（不可抵扣但有据）
    3. 无票（需纳税调整）
    4. 待取票（催促取票）

    直接对应报税时的数据需求。
    """
    service = PlatformFeeInvoiceService(db)
    return await service.get_fee_invoice_summary(platform_id, period)


@router.post("/match-invoice")
async def match_invoice(
    data: InvoiceMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """将发票匹配到平台费用"""
    service = PlatformFeeInvoiceService(db)
    record = await service.match_invoice(
        fee_record_id=data.fee_record_id,
        invoice_id=data.invoice_id,
        invoice_no=data.invoice_no,
        invoice_status=InvoiceStatus(data.invoice_status),
    )
    return {
        "fee_record_id": record.id,
        "invoice_status": record.invoice_status.value,
        "message": "发票匹配成功",
    }


@router.post("/mark-no-invoice")
async def mark_no_invoice(
    data: NoInvoiceMarkRequest,
    db: AsyncSession = Depends(get_db),
):
    """标记为无票并指定税务分类"""
    service = PlatformFeeInvoiceService(db)
    record = await service.mark_no_invoice(
        fee_record_id=data.fee_record_id,
        tax_category=data.tax_category,
    )
    return {
        "fee_record_id": record.id,
        "tax_category": record.no_invoice_tax_category,
        "message": "已标记为无票，汇算清缴时可能需要纳税调增",
    }


@router.get("/deductible-input-tax/{period}")
async def get_deductible_input_tax(
    period: str,
    db: AsyncSession = Depends(get_db),
):
    """获取可抵扣的平台费用进项税额

    直接用于增值税申报表填报。
    """
    service = PlatformFeeInvoiceService(db)
    return await service.get_deductible_input_tax(period)
