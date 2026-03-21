"""订单管理API"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order, OrderItem, OrderStatus, Platform, PlatformType
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    PlatformCreate,
    PlatformResponse,
)
from app.services.accounting_service import AccountingService

router = APIRouter()


@router.post("/platforms", response_model=PlatformResponse)
async def create_platform(
    data: PlatformCreate, db: AsyncSession = Depends(get_db)
):
    """创建电商平台/店铺"""
    platform = Platform(
        name=data.name,
        platform_type=PlatformType(data.platform_type),
        shop_id=data.shop_id,
        commission_rate=data.commission_rate,
        tech_service_fee_rate=data.tech_service_fee_rate,
        remark=data.remark,
    )
    db.add(platform)
    await db.flush()
    return platform


@router.post("", response_model=OrderResponse)
async def create_order(
    data: OrderCreate, db: AsyncSession = Depends(get_db)
):
    """创建订单"""
    order = Order(
        platform_id=data.platform_id,
        order_no=data.order_no,
        platform_order_no=data.platform_order_no,
        status=OrderStatus(data.status),
        total_amount=data.total_amount,
        product_amount=data.product_amount,
        freight_amount=data.freight_amount,
        discount_amount=data.discount_amount,
        platform_discount=data.platform_discount,
        merchant_discount=data.merchant_discount,
        actual_payment=data.actual_payment,
        order_time=data.order_time,
        pay_time=data.pay_time,
    )
    db.add(order)
    await db.flush()

    for item_data in data.items:
        item = OrderItem(
            order_id=order.id,
            sku_code=item_data.sku_code,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=item_data.total_price,
            cost_price=item_data.cost_price,
            tax_rate=item_data.tax_rate,
        )
        db.add(item)

    return order


@router.post("/import/{platform_type}")
async def import_orders(
    platform_type: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """导入平台订单（上传Excel/CSV文件）

    支持：
    - tmall: 天猫/淘宝已卖出的宝贝导出
    - jd: 京东订单导出
    """
    from pathlib import Path
    import tempfile

    from app.services.platform import JDParser, TmallParser

    parsers = {
        "tmall": TmallParser(),
        "taobao": TmallParser(),
        "jd": JDParser(),
    }

    parser = parsers.get(platform_type)
    if not parser:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台类型: {platform_type}",
        )

    # 保存上传文件
    suffix = Path(file.filename).suffix if file.filename else ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        orders = parser.parse_orders(tmp_path)
        return {
            "message": f"成功解析 {len(orders)} 条订单",
            "count": len(orders),
            "sample": orders[:3] if orders else [],
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/{order_id}/confirm-revenue")
async def confirm_order_revenue(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """确认订单收入并生成凭证"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.platform))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    service = AccountingService(db)
    period = (
        order.complete_time.strftime("%Y-%m")
        if order.complete_time
        else order.order_time.strftime("%Y-%m")
    )

    revenue = await service.confirm_revenue(order)
    voucher = await service.generate_sale_voucher(order, period)

    return {
        "revenue": revenue,
        "voucher_no": voucher.voucher_no,
        "message": "收入确认成功，凭证已生成",
    }
