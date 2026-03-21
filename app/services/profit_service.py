"""利润分析服务 - 毛利分析、SKU利润、渠道ROI"""

from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import CostRecord, CostType
from app.models.order import Order, OrderItem, OrderStatus, Platform


class ProfitService:
    """利润分析服务

    电商利润核算公式：
    毛利 = 不含税收入 - 商品成本（不含税）
    毛利率 = 毛利 / 不含税收入 × 100%

    净利润 = 毛利 - 平台佣金 - 推广费 - 物流费 - 包装费 - 人工成本 - 其他
    净利率 = 净利润 / 不含税收入 × 100%

    SKU级利润 = SKU收入 - SKU成本 - 分摊的平台费 - 分摊的物流费
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overall_profit(self, period: str) -> dict:
        """获取整体利润分析

        Args:
            period: 期间，格式 YYYY-MM
        """
        # 查询已完成订单
        orders_result = await self.db.execute(
            select(Order).where(
                Order.status == OrderStatus.COMPLETED,
            )
        )
        orders = [
            o for o in orders_result.scalars().all()
            if o.complete_time and o.complete_time.strftime("%Y-%m") == period
        ]

        # 收入统计
        total_revenue_inc_tax = sum(
            (o.actual_payment + o.platform_discount for o in orders), Decimal("0")
        )
        total_revenue_ex_tax = (
            total_revenue_inc_tax / Decimal("1.13")
        ).quantize(Decimal("0.01"))
        total_refund = sum((o.refund_amount for o in orders), Decimal("0"))

        # 成本统计
        costs_result = await self.db.execute(
            select(CostRecord).where(CostRecord.period == period)
        )
        costs = costs_result.scalars().all()

        cost_by_type = {}
        for cost in costs:
            cost_type = cost.cost_type.value
            cost_by_type[cost_type] = cost_by_type.get(
                cost_type, Decimal("0")
            ) + cost.amount

        total_product_cost = cost_by_type.get("purchase", Decimal("0"))
        total_platform_fee = cost_by_type.get("platform_fee", Decimal("0"))
        total_logistics = cost_by_type.get("logistics", Decimal("0"))
        total_promotion = cost_by_type.get("promotion", Decimal("0"))
        total_packaging = cost_by_type.get("packaging", Decimal("0"))
        total_other = cost_by_type.get("other", Decimal("0"))

        # 计算利润
        gross_profit = total_revenue_ex_tax - total_product_cost
        total_expenses = (
            total_platform_fee + total_logistics + total_promotion
            + total_packaging + total_other
        )
        net_profit = gross_profit - total_expenses

        return {
            "period": period,
            "order_count": len(orders),
            "revenue": {
                "inc_tax": total_revenue_inc_tax,
                "ex_tax": total_revenue_ex_tax,
                "refund": total_refund,
            },
            "costs": {
                "product_cost": total_product_cost,
                "platform_fee": total_platform_fee,
                "logistics": total_logistics,
                "promotion": total_promotion,
                "packaging": total_packaging,
                "other": total_other,
                "total": total_product_cost + total_expenses,
            },
            "profit": {
                "gross_profit": gross_profit,
                "gross_margin": (
                    (gross_profit / total_revenue_ex_tax * 100).quantize(
                        Decimal("0.01")
                    )
                    if total_revenue_ex_tax > 0
                    else Decimal("0")
                ),
                "net_profit": net_profit,
                "net_margin": (
                    (net_profit / total_revenue_ex_tax * 100).quantize(
                        Decimal("0.01")
                    )
                    if total_revenue_ex_tax > 0
                    else Decimal("0")
                ),
            },
        }

    async def get_sku_profit(self, period: str) -> list[dict]:
        """获取SKU级别利润分析"""
        # 查询期间内所有订单商品明细
        result = await self.db.execute(
            select(OrderItem, Order)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.status == OrderStatus.COMPLETED)
        )
        rows = result.all()

        sku_data: dict[str, dict] = {}
        for item, order in rows:
            if not (order.complete_time and
                    order.complete_time.strftime("%Y-%m") == period):
                continue

            sku = item.sku_code
            if sku not in sku_data:
                sku_data[sku] = {
                    "sku_code": sku,
                    "product_name": item.product_name,
                    "quantity": 0,
                    "revenue": Decimal("0"),
                    "cost": Decimal("0"),
                    "refund": Decimal("0"),
                }

            sku_data[sku]["quantity"] += item.quantity - item.refund_quantity
            sku_data[sku]["revenue"] += item.total_price - item.refund_amount
            sku_data[sku]["cost"] += item.cost_price * item.quantity
            sku_data[sku]["refund"] += item.refund_amount

        # 计算每个SKU的利润
        sku_list = []
        for sku, data in sku_data.items():
            revenue_ex_tax = (
                data["revenue"] / Decimal("1.13")
            ).quantize(Decimal("0.01"))
            cost_ex_tax = (
                data["cost"] / Decimal("1.13")
            ).quantize(Decimal("0.01"))
            profit = revenue_ex_tax - cost_ex_tax
            margin = (
                (profit / revenue_ex_tax * 100).quantize(Decimal("0.01"))
                if revenue_ex_tax > 0
                else Decimal("0")
            )

            sku_list.append({
                "sku_code": data["sku_code"],
                "product_name": data["product_name"],
                "quantity": data["quantity"],
                "revenue_ex_tax": revenue_ex_tax,
                "cost_ex_tax": cost_ex_tax,
                "profit": profit,
                "margin": margin,
                "refund_amount": data["refund"],
            })

        # 按利润降序排列
        sku_list.sort(key=lambda x: x["profit"], reverse=True)
        return sku_list

    async def get_platform_roi(self, period: str) -> list[dict]:
        """获取各平台/渠道ROI分析"""
        # 按平台分组统计
        result = await self.db.execute(
            select(
                Platform.id,
                Platform.name,
                Platform.platform_type,
                func.count(Order.id).label("order_count"),
                func.sum(Order.actual_payment).label("total_revenue"),
                func.sum(Order.commission_amount).label("total_commission"),
                func.sum(Order.refund_amount).label("total_refund"),
            )
            .join(Order, Platform.id == Order.platform_id)
            .where(Order.status == OrderStatus.COMPLETED)
            .group_by(Platform.id, Platform.name, Platform.platform_type)
        )
        rows = result.all()

        platform_data = []
        for row in rows:
            revenue = row.total_revenue or Decimal("0")
            commission = row.total_commission or Decimal("0")
            refund = row.total_refund or Decimal("0")

            # 获取该平台的推广费
            promo_result = await self.db.execute(
                select(func.sum(CostRecord.amount)).where(
                    and_(
                        CostRecord.cost_type == CostType.PROMOTION,
                        CostRecord.period == period,
                    )
                )
            )
            promotion_cost = promo_result.scalar() or Decimal("0")

            total_cost = commission + promotion_cost
            roi = (
                ((revenue - total_cost) / total_cost * 100).quantize(
                    Decimal("0.01")
                )
                if total_cost > 0
                else Decimal("0")
            )

            platform_data.append({
                "platform_id": row.id,
                "platform_name": row.name,
                "platform_type": row.platform_type.value,
                "order_count": row.order_count,
                "revenue": revenue,
                "commission": commission,
                "promotion_cost": promotion_cost,
                "refund": refund,
                "total_cost": total_cost,
                "roi": roi,
            })

        return platform_data
