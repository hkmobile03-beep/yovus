"""对账服务 - 平台账单与系统数据对账"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.reconciliation import (
    ReconciliationRecord,
    ReconciliationStatus,
    ReconciliationTask,
)


class ReconciliationService:
    """对账服务

    对账逻辑：
    1. 导入平台结算账单（Excel/CSV）
    2. 按订单号匹配系统订单
    3. 比对金额（订单金额、佣金、结算额）
    4. 标记差异并记录原因
    5. 生成对账报告

    常见差异原因：
    - 佣金费率差异（类目佣金 vs 活动佣金）
    - 退款时间差（跨期退款）
    - 平台扣款（罚款、保证金等）
    - 优惠分摊差异
    """

    # 金额容差（±0.01元以内视为匹配）
    AMOUNT_TOLERANCE = Decimal("0.01")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_reconciliation_task(
        self,
        platform_id: int,
        period_start: date,
        period_end: date,
    ) -> ReconciliationTask:
        """创建对账任务"""
        task = ReconciliationTask(
            platform_id=platform_id,
            period_start=period_start,
            period_end=period_end,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def reconcile_orders(
        self,
        task: ReconciliationTask,
        platform_records: list[dict],
    ) -> dict:
        """执行订单对账

        Args:
            task: 对账任务
            platform_records: 平台账单解析后的记录列表
                每条记录包含: order_no, amount, commission, settlement

        Returns:
            对账结果汇总
        """
        matched = 0
        discrepancy = 0
        not_found = 0
        total_diff = Decimal("0")

        for record in platform_records:
            order_no = record.get("order_no", "")
            if not order_no:
                continue

            # 查找系统订单
            result = await self.db.execute(
                select(Order).where(Order.platform_order_no == order_no)
            )
            order = result.scalar_one_or_none()

            recon_record = ReconciliationRecord(
                task_id=task.id,
                order_no=order_no,
                platform_amount=Decimal(str(record.get("amount", 0))),
                platform_commission=Decimal(str(record.get("commission", 0))),
                platform_settlement=Decimal(str(record.get("settlement", 0))),
            )

            if order is None:
                # 系统中未找到订单
                recon_record.status = ReconciliationStatus.DISCREPANCY
                recon_record.diff_reason = "系统中未找到该订单"
                recon_record.amount_diff = recon_record.platform_amount
                not_found += 1
            else:
                # 填充系统数据
                recon_record.system_amount = order.total_amount
                recon_record.system_commission = order.commission_amount
                recon_record.system_settlement = order.settlement_amount

                # 计算差异
                amount_diff = abs(
                    recon_record.system_amount - recon_record.platform_amount
                )
                commission_diff = abs(
                    recon_record.system_commission - recon_record.platform_commission
                )
                settlement_diff = abs(
                    recon_record.system_settlement - recon_record.platform_settlement
                )

                recon_record.amount_diff = (
                    recon_record.system_amount - recon_record.platform_amount
                )
                recon_record.commission_diff = (
                    recon_record.system_commission - recon_record.platform_commission
                )
                recon_record.settlement_diff = (
                    recon_record.system_settlement - recon_record.platform_settlement
                )

                # 判断是否匹配
                if (
                    amount_diff <= self.AMOUNT_TOLERANCE
                    and commission_diff <= self.AMOUNT_TOLERANCE
                    and settlement_diff <= self.AMOUNT_TOLERANCE
                ):
                    recon_record.status = ReconciliationStatus.MATCHED
                    matched += 1
                else:
                    recon_record.status = ReconciliationStatus.DISCREPANCY
                    recon_record.diff_reason = self._analyze_diff_reason(
                        recon_record
                    )
                    discrepancy += 1
                    total_diff += abs(recon_record.settlement_diff)

            self.db.add(recon_record)

        # 更新任务统计
        task.total_orders = len(platform_records)
        task.matched_orders = matched
        task.discrepancy_orders = discrepancy + not_found
        task.discrepancy_amount = total_diff
        task.status = "completed"

        return {
            "total": len(platform_records),
            "matched": matched,
            "discrepancy": discrepancy,
            "not_found": not_found,
            "match_rate": (
                f"{matched / len(platform_records) * 100:.1f}%"
                if platform_records
                else "0%"
            ),
            "total_discrepancy_amount": total_diff,
        }

    async def find_system_only_orders(
        self,
        platform_id: int,
        period_start: date,
        period_end: date,
        platform_order_nos: set[str],
    ) -> list[Order]:
        """查找系统有但平台账单没有的订单（可能漏结算）"""
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.platform_id == platform_id,
                    Order.complete_time >= period_start,
                    Order.complete_time <= period_end,
                    Order.platform_order_no.notin_(platform_order_nos),
                )
            )
        )
        return list(result.scalars().all())

    def _analyze_diff_reason(self, record: ReconciliationRecord) -> str:
        """分析差异原因"""
        reasons = []

        if abs(record.commission_diff) > self.AMOUNT_TOLERANCE:
            reasons.append(
                f"佣金差异{record.commission_diff}元"
                "（可能原因：活动佣金费率、类目调整）"
            )

        if abs(record.amount_diff) > self.AMOUNT_TOLERANCE:
            reasons.append(
                f"订单金额差异{record.amount_diff}元"
                "（可能原因：退款、优惠分摊）"
            )

        if (
            abs(record.settlement_diff) > self.AMOUNT_TOLERANCE
            and abs(record.amount_diff) <= self.AMOUNT_TOLERANCE
        ):
            reasons.append(
                f"结算差异{record.settlement_diff}元"
                "（可能原因：平台扣款、配送费）"
            )

        return "；".join(reasons) if reasons else "未知差异"

    async def get_reconciliation_summary(
        self, task_id: int
    ) -> dict:
        """获取对账汇总报告"""
        result = await self.db.execute(
            select(ReconciliationRecord).where(
                ReconciliationRecord.task_id == task_id
            )
        )
        records = result.scalars().all()

        status_count = {}
        total_amount_diff = Decimal("0")
        total_commission_diff = Decimal("0")
        total_settlement_diff = Decimal("0")

        for r in records:
            status_count[r.status.value] = status_count.get(r.status.value, 0) + 1
            total_amount_diff += r.amount_diff
            total_commission_diff += r.commission_diff
            total_settlement_diff += r.settlement_diff

        return {
            "total_records": len(records),
            "status_breakdown": status_count,
            "total_amount_diff": total_amount_diff,
            "total_commission_diff": total_commission_diff,
            "total_settlement_diff": total_settlement_diff,
        }
