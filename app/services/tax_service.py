"""税务服务 - 增值税、企业所得税、附加税计算与申报数据生成"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tax import (
    InvoiceDirection,
    TaxDeclaration,
    TaxDeclarationItem,
    TaxType,
    VATInvoice,
)


class TaxService:
    """税务服务

    一般纳税人增值税计算：
    应纳税额 = 销项税额 - 进项税额
    销项税额 = 不含税销售额 × 税率
    进项税额 = 取得的增值税专用发票上注明的税额

    附加税（以增值税为税基）：
    城市维护建设税 = 增值税 × 7%
    教育费附加 = 增值税 × 3%
    地方教育附加 = 增值税 × 2%

    企业所得税：
    应纳税所得额 = 收入总额 - 不征税收入 - 免税收入 - 各项扣除 - 弥补亏损
    应纳税额 = 应纳税所得额 × 25%
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_vat(self, period: str) -> dict[str, Decimal]:
        """计算增值税

        Args:
            period: 申报期间，格式 YYYY-MM

        Returns:
            output_tax: 销项税额
            input_tax: 进项税额
            tax_payable: 应纳税额
            carried_forward: 留抵税额（进项大于销项时）
        """
        # 查询销项发票
        output_result = await self.db.execute(
            select(VATInvoice).where(
                and_(
                    VATInvoice.direction == InvoiceDirection.OUTPUT,
                    VATInvoice.period == period,
                )
            )
        )
        output_invoices = output_result.scalars().all()

        # 查询已认证的进项发票
        input_result = await self.db.execute(
            select(VATInvoice).where(
                and_(
                    VATInvoice.direction == InvoiceDirection.INPUT,
                    VATInvoice.period == period,
                    VATInvoice.is_certified == True,
                )
            )
        )
        input_invoices = input_result.scalars().all()

        # 计算销项税额
        output_amount = sum(
            (inv.amount for inv in output_invoices), Decimal("0")
        )
        output_tax = sum(
            (inv.tax_amount for inv in output_invoices), Decimal("0")
        )

        # 计算进项税额
        input_amount = sum(
            (inv.amount for inv in input_invoices), Decimal("0")
        )
        input_tax = sum(
            (inv.tax_amount for inv in input_invoices), Decimal("0")
        )

        # 应纳税额
        tax_payable = output_tax - input_tax
        carried_forward = Decimal("0")

        if tax_payable < 0:
            # 进项大于销项，产生留抵
            carried_forward = abs(tax_payable)
            tax_payable = Decimal("0")

        return {
            "output_amount": output_amount,
            "output_tax": output_tax,
            "output_invoice_count": len(output_invoices),
            "input_amount": input_amount,
            "input_tax": input_tax,
            "input_invoice_count": len(input_invoices),
            "tax_payable": tax_payable,
            "carried_forward": carried_forward,
        }

    async def calculate_surcharges(
        self, vat_amount: Decimal
    ) -> dict[str, Decimal]:
        """计算附加税

        以实际缴纳的增值税为税基计算。
        """
        urban_tax = (
            vat_amount * settings.urban_maintenance_tax_rate
        ).quantize(Decimal("0.01"))
        education = (
            vat_amount * settings.education_surcharge_rate
        ).quantize(Decimal("0.01"))
        local_education = (
            vat_amount * settings.local_education_surcharge_rate
        ).quantize(Decimal("0.01"))

        return {
            "urban_maintenance_tax": urban_tax,
            "education_surcharge": education,
            "local_education_surcharge": local_education,
            "total_surcharges": urban_tax + education + local_education,
        }

    async def calculate_corporate_income_tax(
        self,
        period: str,
        total_revenue: Decimal,
        total_cost: Decimal,
        total_expense: Decimal,
        prior_losses: Decimal = Decimal("0"),
    ) -> dict[str, Decimal]:
        """计算企业所得税（季度预缴）

        一般企业税率25%
        小型微利企业优惠：应纳税所得额≤300万，实际税率5%/10%

        注：电商企业常见扣除项：
        - 广告宣传费（不超过营收15%可扣除）
        - 业务招待费（实际发生额60%且不超过营收0.5%）
        """
        taxable_income = total_revenue - total_cost - total_expense - prior_losses

        if taxable_income <= 0:
            return {
                "total_revenue": total_revenue,
                "total_deductions": total_cost + total_expense,
                "prior_losses": prior_losses,
                "taxable_income": Decimal("0"),
                "tax_rate": settings.corporate_income_tax_rate,
                "tax_payable": Decimal("0"),
            }

        # 小型微利企业优惠判断（简化：仅按应纳税所得额判断）
        if taxable_income <= Decimal("1000000"):
            # 应纳税所得额≤100万：减按25%计入，税率20% → 实际5%
            effective_rate = Decimal("0.05")
        elif taxable_income <= Decimal("3000000"):
            # 100万<应纳税所得额≤300万：减按50%计入，税率20% → 实际10%
            effective_rate = Decimal("0.10")
        else:
            effective_rate = settings.corporate_income_tax_rate

        tax_payable = (taxable_income * effective_rate).quantize(Decimal("0.01"))

        return {
            "total_revenue": total_revenue,
            "total_deductions": total_cost + total_expense,
            "prior_losses": prior_losses,
            "taxable_income": taxable_income,
            "tax_rate": effective_rate,
            "tax_payable": tax_payable,
        }

    async def generate_vat_declaration(self, period: str) -> TaxDeclaration:
        """生成增值税纳税申报表"""
        vat = await self.calculate_vat(period)
        surcharges = await self.calculate_surcharges(vat["tax_payable"])

        declaration = TaxDeclaration(
            tax_type=TaxType.VAT,
            period=period,
            taxable_income=vat["output_amount"],
            tax_payable=vat["output_tax"],
            tax_deductible=vat["input_tax"],
            tax_due=vat["tax_payable"],
        )
        self.db.add(declaration)
        await self.db.flush()

        # 申报表栏次
        items = [
            TaxDeclarationItem(
                declaration_id=declaration.id,
                item_name="销售额（不含税）",
                item_code="1",
                amount=vat["output_amount"],
            ),
            TaxDeclarationItem(
                declaration_id=declaration.id,
                item_name="销项税额",
                item_code="11",
                tax_amount=vat["output_tax"],
            ),
            TaxDeclarationItem(
                declaration_id=declaration.id,
                item_name="进项税额",
                item_code="12",
                tax_amount=vat["input_tax"],
            ),
            TaxDeclarationItem(
                declaration_id=declaration.id,
                item_name="应纳税额",
                item_code="19",
                tax_amount=vat["tax_payable"],
            ),
            TaxDeclarationItem(
                declaration_id=declaration.id,
                item_name="期末留抵税额",
                item_code="20",
                tax_amount=vat["carried_forward"],
            ),
        ]

        # 附加税
        for tax_name, tax_amount in [
            ("城市维护建设税", surcharges["urban_maintenance_tax"]),
            ("教育费附加", surcharges["education_surcharge"]),
            ("地方教育附加", surcharges["local_education_surcharge"]),
        ]:
            items.append(
                TaxDeclarationItem(
                    declaration_id=declaration.id,
                    item_name=tax_name,
                    tax_amount=tax_amount,
                )
            )

        for item in items:
            self.db.add(item)

        return declaration
