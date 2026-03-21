"""核算服务 - 收入确认、成本归集、凭证生成"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import (
    AccountingVoucher,
    CostRecord,
    CostType,
    VoucherEntry,
    VoucherType,
)
from app.models.order import Order, OrderItem, OrderStatus


class AccountingService:
    """核算服务

    收入确认原则（电商）：
    - 确认收货时点确认收入（权责发生制）
    - 收入 = 实付金额 - 平台承担优惠（不含税）
    - 增值税销项 = 收入 × 税率 / (1 + 税率)

    成本核算：
    - 商品成本 = 采购成本 × 数量
    - 平台费用 = 佣金 + 技术服务费
    - 物流成本 = 快递费 + 包装费
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def confirm_revenue(self, order: Order) -> dict[str, Decimal]:
        """确认收入（价税分离）

        一般纳税人增值税计算：
        含税收入 = 实付金额 - 平台承担优惠部分
        不含税收入 = 含税收入 / (1 + 税率)
        增值税销项税额 = 含税收入 - 不含税收入

        Returns:
            revenue_ex_tax: 不含税收入
            vat_output: 增值税销项税额
            revenue_inc_tax: 含税收入
        """
        # 含税收入 = 买家实付 + 平台承担优惠（平台补贴也是商家收入来源）
        revenue_inc_tax = order.actual_payment + order.platform_discount

        # 按订单商品加权计算不含税收入
        total_revenue_ex_tax = Decimal("0")
        total_vat = Decimal("0")

        items = order.items
        if items:
            for item in items:
                item_revenue = (
                    item.total_price - item.refund_amount
                )
                tax_rate = item.tax_rate
                item_ex_tax = (item_revenue / (1 + tax_rate)).quantize(
                    Decimal("0.01")
                )
                item_vat = item_revenue - item_ex_tax
                total_revenue_ex_tax += item_ex_tax
                total_vat += item_vat
        else:
            # 无明细时按默认13%税率
            tax_rate = Decimal("0.13")
            total_revenue_ex_tax = (
                revenue_inc_tax / (1 + tax_rate)
            ).quantize(Decimal("0.01"))
            total_vat = revenue_inc_tax - total_revenue_ex_tax

        return {
            "revenue_inc_tax": revenue_inc_tax,
            "revenue_ex_tax": total_revenue_ex_tax,
            "vat_output": total_vat,
        }

    async def calculate_order_cost(self, order: Order) -> dict[str, Decimal]:
        """计算订单成本

        订单成本构成：
        1. 商品采购成本（不含税） = 含税成本 / (1 + 进项税率)
        2. 平台佣金（不可抵扣进项税）
        3. 物流成本
        4. 包装成本
        """
        product_cost = Decimal("0")
        logistics_cost = Decimal("0")
        packaging_cost = Decimal("0")
        input_vat = Decimal("0")  # 可抵扣进项税

        for item in order.items:
            # 商品成本
            item_cost = item.cost_price * item.quantity
            product_cost += item_cost

            # 假设采购有专票可抵扣13%
            cost_ex_tax = (item_cost / Decimal("1.13")).quantize(Decimal("0.01"))
            input_vat += item_cost - cost_ex_tax

        platform_fee = order.commission_amount

        return {
            "product_cost": product_cost,
            "platform_fee": platform_fee,
            "logistics_cost": logistics_cost,
            "packaging_cost": packaging_cost,
            "input_vat": input_vat,
            "total_cost": product_cost + platform_fee + logistics_cost + packaging_cost,
        }

    async def generate_sale_voucher(
        self, order: Order, period: str
    ) -> AccountingVoucher:
        """生成销售收入凭证

        借：应收账款-平台（结算金额）
            销售费用-佣金（平台佣金）
           贷：主营业务收入（不含税收入）
               应交税费-应交增值税(销项税额)

        同时生成成本结转凭证：
        借：主营业务成本
           贷：库存商品
        """
        revenue = await self.confirm_revenue(order)
        costs = await self.calculate_order_cost(order)

        voucher_no = f"SR-{period}-{order.order_no[-6:]}"

        voucher = AccountingVoucher(
            voucher_no=voucher_no,
            voucher_type=VoucherType.GENERAL,
            voucher_date=order.complete_time.date() if order.complete_time else date.today(),
            period=period,
            summary=f"销售收入-{order.platform.name if order.platform else ''}-{order.order_no}",
            total_debit=revenue["revenue_inc_tax"],
            total_credit=revenue["revenue_inc_tax"],
            source_type="order",
            source_id=order.id,
        )

        entries = [
            # 借：应收账款-平台
            VoucherEntry(
                account_code="1122",
                account_name="应收账款",
                summary=f"平台结算款-{order.order_no}",
                debit_amount=order.settlement_amount,
                credit_amount=Decimal("0"),
                seq=1,
            ),
            # 借：销售费用-平台佣金
            VoucherEntry(
                account_code="6601",
                account_name="销售费用-平台佣金",
                summary=f"平台佣金-{order.order_no}",
                debit_amount=order.commission_amount,
                credit_amount=Decimal("0"),
                seq=2,
            ),
            # 贷：主营业务收入
            VoucherEntry(
                account_code="6001",
                account_name="主营业务收入",
                summary=f"销售收入-{order.order_no}",
                debit_amount=Decimal("0"),
                credit_amount=revenue["revenue_ex_tax"],
                seq=3,
            ),
            # 贷：应交税费-增值税(销项)
            VoucherEntry(
                account_code="222101",
                account_name="应交税费-应交增值税(销项税额)",
                summary=f"销项税额-{order.order_no}",
                debit_amount=Decimal("0"),
                credit_amount=revenue["vat_output"],
                seq=4,
            ),
        ]

        voucher.entries = entries
        self.db.add(voucher)

        # 记录成本
        cost_record = CostRecord(
            order_id=order.id,
            cost_type=CostType.PURCHASE,
            amount=costs["product_cost"],
            tax_amount=costs["input_vat"],
            period=period,
            remark=f"订单{order.order_no}商品成本",
        )
        self.db.add(cost_record)

        if order.commission_amount > 0:
            fee_record = CostRecord(
                order_id=order.id,
                cost_type=CostType.PLATFORM_FEE,
                amount=order.commission_amount,
                tax_amount=Decimal("0"),
                period=period,
                remark=f"订单{order.order_no}平台佣金",
            )
            self.db.add(fee_record)

        return voucher

    async def get_period_summary(self, period: str) -> dict[str, Decimal]:
        """获取期间汇总数据"""
        result = await self.db.execute(
            select(Order).where(
                Order.status == OrderStatus.COMPLETED,
            )
        )
        orders = result.scalars().all()

        total_revenue = Decimal("0")
        total_cost = Decimal("0")
        total_commission = Decimal("0")
        total_refund = Decimal("0")
        order_count = 0

        for order in orders:
            if order.complete_time and order.complete_time.strftime("%Y-%m") == period:
                revenue = await self.confirm_revenue(order)
                costs = await self.calculate_order_cost(order)
                total_revenue += revenue["revenue_ex_tax"]
                total_cost += costs["total_cost"]
                total_commission += order.commission_amount
                total_refund += order.refund_amount
                order_count += 1

        return {
            "period": period,
            "order_count": order_count,
            "total_revenue_ex_tax": total_revenue,
            "total_cost": total_cost,
            "total_commission": total_commission,
            "total_refund": total_refund,
            "gross_profit": total_revenue - total_cost,
            "gross_margin": (
                (total_revenue - total_cost) / total_revenue * 100
                if total_revenue > 0
                else Decimal("0")
            ).quantize(Decimal("0.01")),
        }
