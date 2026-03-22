"""双口径收入计算服务

核心业务逻辑：

【口径一：创建订单口径（商家/ERP 口径）】
  统计范围 = 当月1日00:00:00 ~ 当月末日23:59:59 创建的订单
  收入金额 = 创建订单总额 - 同期间内退款完成的金额
  ↑ 这是你们目前申报和ERP对账使用的口径

【口径二：确认收货口径（平台涉税推送口径）】
  统计范围 = 当月内买家确认收货（交易成功）的订单
  收入金额 = 确认收货的订单金额
  ↑ 这是平台现在推送给税务局的涉税金额口径

两种口径产生差异的原因：
  - 月初创建、下月确收 → 口径一有，口径二无
  - 上月创建、本月确收 → 口径一无，口径二有
  - 跨月退款 → 退款计入不同期间
  - 未确收订单 → 口径一有，口径二无
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus


class RevenueCalibration(str, enum.Enum):
    """收入确认口径"""
    ORDER_CREATION = "order_creation"       # 创建订单口径（你们的口径）
    CONFIRMED_RECEIPT = "confirmed_receipt"  # 确认收货口径（平台口径）


class RevenueCalibrationService:
    """双口径收入计算服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_revenue(
        self,
        platform_id: int | None,
        period_start: datetime,
        period_end: datetime,
        calibration: RevenueCalibration,
    ) -> dict:
        """按指定口径计算收入

        Args:
            platform_id: 平台ID（None则汇总所有平台）
            period_start: 期间开始（当月1日 00:00:00）
            period_end: 期间结束（当月末日 23:59:59）
            calibration: 口径类型
        """
        if calibration == RevenueCalibration.ORDER_CREATION:
            return await self._calc_order_creation_basis(
                platform_id, period_start, period_end
            )
        else:
            return await self._calc_confirmed_receipt_basis(
                platform_id, period_start, period_end
            )

    async def _calc_order_creation_basis(
        self,
        platform_id: int | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """【口径一】创建订单口径

        计算逻辑：
        1. 查询期间内创建（order_time）的所有已付款订单 → 订单总额
        2. 查询期间内退款完成（refund_complete_time）的订单 → 退款总额
        3. 应税收入 = 订单总额 - 退款总额

        注意：退款订单可能是之前月份创建的，但在本月完成退款
        """
        # 条件构建
        base_conditions = []
        if platform_id:
            base_conditions.append(Order.platform_id == platform_id)

        # 1. 期间内创建的订单（排除取消/待付款的）
        order_conditions = [
            Order.order_time >= period_start,
            Order.order_time <= period_end,
            Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.PENDING]),
        ] + base_conditions

        order_result = await self.db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.actual_payment), 0).label("total_amount"),
                func.coalesce(func.sum(Order.product_amount), 0).label("product_amount"),
                func.coalesce(func.sum(Order.freight_amount), 0).label("freight_amount"),
                func.coalesce(func.sum(Order.discount_amount), 0).label("discount_amount"),
                func.coalesce(func.sum(Order.platform_discount), 0).label("platform_discount"),
            ).where(and_(*order_conditions))
        )
        order_row = order_result.one()

        # 2. 期间内退款完成的订单
        refund_conditions = [
            Order.refund_complete_time >= period_start,
            Order.refund_complete_time <= period_end,
            Order.refund_amount > 0,
        ] + base_conditions

        refund_result = await self.db.execute(
            select(
                func.count(Order.id).label("refund_count"),
                func.coalesce(func.sum(Order.refund_amount), 0).label("refund_amount"),
            ).where(and_(*refund_conditions))
        )
        refund_row = refund_result.one()

        gross_amount = Decimal(str(order_row.total_amount))
        refund_amount = Decimal(str(refund_row.refund_amount))
        net_amount = gross_amount - refund_amount

        # 价税分离
        tax_rate = Decimal("0.13")
        net_ex_tax = (net_amount / (1 + tax_rate)).quantize(Decimal("0.01"))
        vat = net_amount - net_ex_tax

        return {
            "calibration": "order_creation",
            "calibration_label": "创建订单口径（商家/ERP口径）",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "order_count": order_row.order_count,
            "gross_amount": gross_amount,
            "gross_product_amount": Decimal(str(order_row.product_amount)),
            "gross_freight": Decimal(str(order_row.freight_amount)),
            "gross_discount": Decimal(str(order_row.discount_amount)),
            "platform_discount": Decimal(str(order_row.platform_discount)),
            "refund_count": refund_row.refund_count,
            "refund_amount": refund_amount,
            "net_amount_inc_tax": net_amount,
            "net_amount_ex_tax": net_ex_tax,
            "vat_output": vat,
        }

    async def _calc_confirmed_receipt_basis(
        self,
        platform_id: int | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """【口径二】确认收货口径（平台涉税推送口径）

        计算逻辑：
        1. 查询期间内确认收货（complete_time）的订单
        2. 收入 = 确收订单的实付金额（已扣除该订单的退款）
        """
        conditions = [
            Order.complete_time >= period_start,
            Order.complete_time <= period_end,
            Order.status == OrderStatus.COMPLETED,
        ]
        if platform_id:
            conditions.append(Order.platform_id == platform_id)

        result = await self.db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.actual_payment), 0).label("total_amount"),
                func.coalesce(func.sum(Order.refund_amount), 0).label("refund_amount"),
                func.coalesce(func.sum(Order.product_amount), 0).label("product_amount"),
                func.coalesce(func.sum(Order.commission_amount), 0).label("commission_amount"),
                func.coalesce(func.sum(Order.settlement_amount), 0).label("settlement_amount"),
            ).where(and_(*conditions))
        )
        row = result.one()

        total = Decimal(str(row.total_amount))
        refund = Decimal(str(row.refund_amount))
        net_amount = total - refund

        tax_rate = Decimal("0.13")
        net_ex_tax = (net_amount / (1 + tax_rate)).quantize(Decimal("0.01"))
        vat = net_amount - net_ex_tax

        return {
            "calibration": "confirmed_receipt",
            "calibration_label": "确认收货口径（平台涉税推送口径）",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "order_count": row.order_count,
            "gross_amount": total,
            "refund_amount": refund,
            "net_amount_inc_tax": net_amount,
            "net_amount_ex_tax": net_ex_tax,
            "vat_output": vat,
            "commission_total": Decimal(str(row.commission_amount)),
            "settlement_total": Decimal(str(row.settlement_amount)),
        }

    async def compare_calibrations(
        self,
        platform_id: int | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """双口径对比分析

        同时计算两种口径，输出差异明细，帮你理解：
        - 差多少钱
        - 差在哪里（哪些订单导致的）
        - 如何调节
        """
        creation = await self.calculate_revenue(
            platform_id, period_start, period_end,
            RevenueCalibration.ORDER_CREATION,
        )
        receipt = await self.calculate_revenue(
            platform_id, period_start, period_end,
            RevenueCalibration.CONFIRMED_RECEIPT,
        )

        diff_inc_tax = (
            creation["net_amount_inc_tax"] - receipt["net_amount_inc_tax"]
        )
        diff_ex_tax = (
            creation["net_amount_ex_tax"] - receipt["net_amount_ex_tax"]
        )

        # 找出造成差异的订单
        diff_orders = await self._find_calibration_diff_orders(
            platform_id, period_start, period_end
        )

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "creation_basis": creation,
            "receipt_basis": receipt,
            "difference": {
                "net_amount_inc_tax_diff": diff_inc_tax,
                "net_amount_ex_tax_diff": diff_ex_tax,
                "creation_higher": diff_inc_tax > 0,
                "abs_diff": abs(diff_inc_tax),
                "explanation": self._explain_diff(diff_inc_tax),
            },
            "diff_detail": diff_orders,
        }

    async def _find_calibration_diff_orders(
        self,
        platform_id: int | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """找出两种口径之间差异的具体订单

        差异来源：
        A类：本月创建、但未在本月确收 → 仅在口径一
        B类：非本月创建、但在本月确收 → 仅在口径二
        C类：退款时间跨月 → 两个口径都有但金额不同
        """
        base_cond = []
        if platform_id:
            base_cond.append(Order.platform_id == platform_id)

        # A类：本月创建 & （未确收 或 确收不在本月）
        a_conditions = [
            Order.order_time >= period_start,
            Order.order_time <= period_end,
            Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.PENDING]),
            or_(
                Order.complete_time == None,  # noqa: E711 (SQLAlchemy IS NULL)
                Order.complete_time < period_start,
                Order.complete_time > period_end,
            ),
        ] + base_cond

        a_result = await self.db.execute(
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.actual_payment), 0).label("amount"),
            ).where(and_(*a_conditions))
        )
        a_row = a_result.one()

        # B类：确收在本月 & 创建不在本月
        b_conditions = [
            Order.complete_time >= period_start,
            Order.complete_time <= period_end,
            Order.status == OrderStatus.COMPLETED,
            or_(
                Order.order_time < period_start,
                Order.order_time > period_end,
            ),
        ] + base_cond

        b_result = await self.db.execute(
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.actual_payment), 0).label("amount"),
            ).where(and_(*b_conditions))
        )
        b_row = b_result.one()

        # C类：退款跨月（本月创建的订单，退款在非本月完成 或 反之）
        c_refund_out = await self.db.execute(
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.refund_amount), 0).label("amount"),
            ).where(and_(
                Order.order_time >= period_start,
                Order.order_time <= period_end,
                Order.refund_amount > 0,
                or_(
                    Order.refund_complete_time == None,  # noqa: E711 (SQLAlchemy IS NULL)
                    Order.refund_complete_time < period_start,
                    Order.refund_complete_time > period_end,
                ),
                *base_cond,
            ))
        )
        c_out_row = c_refund_out.one()

        c_refund_in = await self.db.execute(
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.refund_amount), 0).label("amount"),
            ).where(and_(
                Order.refund_complete_time >= period_start,
                Order.refund_complete_time <= period_end,
                Order.refund_amount > 0,
                or_(
                    Order.order_time < period_start,
                    Order.order_time > period_end,
                ),
                *base_cond,
            ))
        )
        c_in_row = c_refund_in.one()

        return {
            "type_a_creation_only": {
                "description": "本月创建但未在本月确收的订单（仅创建口径包含）",
                "count": a_row.count,
                "amount": Decimal(str(a_row.amount)),
            },
            "type_b_receipt_only": {
                "description": "非本月创建但在本月确收的订单（仅确收口径包含）",
                "count": b_row.count,
                "amount": Decimal(str(b_row.amount)),
            },
            "type_c_refund_cross_month": {
                "description": "退款跨月差异",
                "refund_out": {
                    "description": "本月创建订单的退款在非本月完成",
                    "count": c_out_row.count,
                    "amount": Decimal(str(c_out_row.amount)),
                },
                "refund_in": {
                    "description": "非本月创建订单的退款在本月完成",
                    "count": c_in_row.count,
                    "amount": Decimal(str(c_in_row.amount)),
                },
            },
        }

    @staticmethod
    def _explain_diff(diff: Decimal) -> str:
        """生成差异说明"""
        if diff == 0:
            return "两种口径金额一致，无差异"
        elif diff > 0:
            return (
                f"创建订单口径比确收口径多{diff}元。"
                "通常原因：本月有新创建订单尚未确认收货（在途订单），"
                "或本月退款完成的订单对应的是之前月份确收的。"
                "与平台涉税推送对账时需关注此差异。"
            )
        else:
            return (
                f"确收口径比创建订单口径多{abs(diff)}元。"
                "通常原因：本月确收了上月或更早创建的订单，"
                "这部分在创建口径中已计入上期。"
                "若按创建口径申报，需与平台涉税数据做调节说明。"
            )
