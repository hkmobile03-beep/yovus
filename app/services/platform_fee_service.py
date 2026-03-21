"""平台费用发票匹配服务

解决的问题：
- 平台扣了哪些费（佣金、推广费、技术服务费、配送费...）
- 哪些费用平台会开发票（专票可抵扣 / 普票不可抵扣）
- 哪些是无票支出（需要按规定做税务处理）
- 每个月各类费用汇总，分有票/无票两组，供报税使用

淘宝/天猫开票规律：
- 佣金（软件服务费）：每月出账单，可申请专票，税率6%
- 直通车/引力魔方/万相台：推广费，每月可开专票，税率6%
- 技术服务费（年费）：年度结算，开专票，税率6%

京东开票规律：
- 佣金（平台使用费）：每月结算后开专票，税率6%
- 京东快车等推广：每月可开专票，税率6%
- 京东物流配送费：每月开专票，税率9%（运输服务）
"""

from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_fee import (
    InvoiceStatus,
    PlatformFeeInvoiceRule,
    PlatformFeeRecord,
    PlatformFeeType,
)


class PlatformFeeInvoiceService:
    """平台费用发票匹配服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_fee_invoice_summary(
        self, platform_id: int | None, period: str
    ) -> dict:
        """获取期间内平台费用的发票匹配汇总

        返回结构：
        - 有专票（可抵扣进项税）的费用汇总
        - 有普票（不可抵扣但有凭证）的费用汇总
        - 无票费用汇总（需特殊税务处理）
        - 待取票费用

        这直接对应到报税时需要填的数据。
        """
        conditions = [PlatformFeeRecord.period == period]
        if platform_id:
            conditions.append(PlatformFeeRecord.platform_id == platform_id)

        result = await self.db.execute(
            select(
                PlatformFeeRecord.invoice_status,
                PlatformFeeRecord.fee_type,
                func.count(PlatformFeeRecord.id).label("count"),
                func.sum(PlatformFeeRecord.amount).label("total_amount"),
                func.sum(PlatformFeeRecord.amount_ex_tax).label("total_ex_tax"),
                func.sum(PlatformFeeRecord.tax_amount).label("total_tax"),
            )
            .where(and_(*conditions))
            .group_by(
                PlatformFeeRecord.invoice_status,
                PlatformFeeRecord.fee_type,
            )
        )
        rows = result.all()

        # 按发票状态分组汇总
        has_special = []  # 有专票，可抵扣
        has_general = []  # 有普票，不可抵扣
        no_invoice = []   # 无票
        pending = []      # 待取票

        total_deductible_tax = Decimal("0")
        total_non_deductible = Decimal("0")
        total_no_invoice = Decimal("0")

        for row in rows:
            item = {
                "fee_type": row.fee_type.value,
                "fee_type_label": self._fee_type_label(row.fee_type),
                "count": row.count,
                "total_amount": Decimal(str(row.total_amount or 0)),
                "total_ex_tax": Decimal(str(row.total_ex_tax or 0)),
                "total_tax": Decimal(str(row.total_tax or 0)),
            }

            if row.invoice_status == InvoiceStatus.HAS_SPECIAL:
                has_special.append(item)
                total_deductible_tax += item["total_tax"]
            elif row.invoice_status == InvoiceStatus.HAS_GENERAL:
                has_general.append(item)
                total_non_deductible += item["total_amount"]
            elif row.invoice_status == InvoiceStatus.NO_INVOICE:
                no_invoice.append(item)
                total_no_invoice += item["total_amount"]
            elif row.invoice_status == InvoiceStatus.PENDING:
                pending.append(item)

        return {
            "period": period,
            "has_special_invoice": {
                "label": "有专票（可抵扣进项税6%）",
                "items": has_special,
                "total_deductible_tax": total_deductible_tax,
                "tax_treatment": "计入应交税费-应交增值税(进项税额)，可抵扣销项",
            },
            "has_general_invoice": {
                "label": "有普票（不可抵扣，全额计入费用）",
                "items": has_general,
                "total_amount": total_non_deductible,
                "tax_treatment": "全额计入销售费用/管理费用，不可抵扣进项",
            },
            "no_invoice": {
                "label": "无票支出（需特殊税务处理）",
                "items": no_invoice,
                "total_amount": total_no_invoice,
                "tax_treatment": (
                    "企业所得税前扣除需满足条件："
                    "500元以下可用收据入账；"
                    "500元以上原则上需发票才能税前扣除。"
                    "无票部分在汇算清缴时可能需要纳税调增。"
                ),
            },
            "pending_invoice": {
                "label": "待取票（尚未取得发票）",
                "items": pending,
                "action": "请及时向平台索取发票，避免影响进项抵扣",
            },
        }

    async def record_platform_fee(
        self,
        platform_id: int,
        fee_type: PlatformFeeType,
        amount: Decimal,
        fee_date,
        period: str,
        description: str | None = None,
        invoice_status: InvoiceStatus = InvoiceStatus.PENDING,
        tax_rate: Decimal = Decimal("0.06"),
    ) -> PlatformFeeRecord:
        """记录一笔平台费用"""
        amount_ex_tax = (amount / (1 + tax_rate)).quantize(Decimal("0.01"))
        tax_amount = amount - amount_ex_tax

        record = PlatformFeeRecord(
            platform_id=platform_id,
            fee_type=fee_type,
            period=period,
            amount=amount,
            amount_ex_tax=amount_ex_tax,
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            invoice_status=invoice_status,
            fee_date=fee_date,
            description=description,
        )
        self.db.add(record)
        return record

    async def match_invoice(
        self,
        fee_record_id: int,
        invoice_id: int,
        invoice_no: str,
        invoice_status: InvoiceStatus,
    ) -> PlatformFeeRecord:
        """将发票匹配到平台费用记录"""
        result = await self.db.execute(
            select(PlatformFeeRecord).where(
                PlatformFeeRecord.id == fee_record_id
            )
        )
        record = result.scalar_one()
        record.invoice_id = invoice_id
        record.invoice_no = invoice_no
        record.invoice_status = invoice_status
        return record

    async def mark_no_invoice(
        self,
        fee_record_id: int,
        tax_category: str,
    ) -> PlatformFeeRecord:
        """标记为无票并指定税务分类"""
        result = await self.db.execute(
            select(PlatformFeeRecord).where(
                PlatformFeeRecord.id == fee_record_id
            )
        )
        record = result.scalar_one()
        record.invoice_status = InvoiceStatus.NO_INVOICE
        record.no_invoice_tax_category = tax_category
        return record

    async def get_deductible_input_tax(self, period: str) -> dict:
        """获取可抵扣的平台费用进项税额（报税用）

        这个数据直接用于增值税申报表的进项税额部分。
        """
        result = await self.db.execute(
            select(
                PlatformFeeRecord.fee_type,
                func.sum(PlatformFeeRecord.tax_amount).label("tax_total"),
                func.sum(PlatformFeeRecord.amount_ex_tax).label("amount_total"),
            )
            .where(
                and_(
                    PlatformFeeRecord.period == period,
                    PlatformFeeRecord.invoice_status == InvoiceStatus.HAS_SPECIAL,
                )
            )
            .group_by(PlatformFeeRecord.fee_type)
        )
        rows = result.all()

        items = []
        total_input_tax = Decimal("0")
        for row in rows:
            tax = Decimal(str(row.tax_total or 0))
            items.append({
                "fee_type": row.fee_type.value,
                "fee_type_label": self._fee_type_label(row.fee_type),
                "amount_ex_tax": Decimal(str(row.amount_total or 0)),
                "input_tax": tax,
            })
            total_input_tax += tax

        return {
            "period": period,
            "items": items,
            "total_input_tax": total_input_tax,
            "note": "此进项税额来自平台费用专用发票，可在增值税申报时抵扣",
        }

    @staticmethod
    def _fee_type_label(fee_type: PlatformFeeType) -> str:
        labels = {
            PlatformFeeType.COMMISSION: "佣金（软件服务费/平台使用费）",
            PlatformFeeType.TECH_SERVICE_FEE: "技术服务费（年费）",
            PlatformFeeType.PROMOTION_ZHITONGCHE: "直通车推广费",
            PlatformFeeType.PROMOTION_ZUANSHI: "钻石展位/引力魔方推广费",
            PlatformFeeType.PROMOTION_WANXIANGTAI: "万相台推广费",
            PlatformFeeType.PROMOTION_JDKUAICHE: "京东快车推广费",
            PlatformFeeType.PROMOTION_JDJINGXUAN: "京东京选推广费",
            PlatformFeeType.DELIVERY_FEE: "配送费（物流费）",
            PlatformFeeType.STORAGE_FEE: "仓储费",
            PlatformFeeType.PENALTY: "罚款/扣款",
            PlatformFeeType.DEPOSIT: "保证金",
            PlatformFeeType.OTHER: "其他费用",
        }
        return labels.get(fee_type, fee_type.value)
