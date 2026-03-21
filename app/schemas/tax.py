"""税务相关Schema"""

from decimal import Decimal

from pydantic import BaseModel


class VATCalculation(BaseModel):
    output_amount: Decimal
    output_tax: Decimal
    output_invoice_count: int
    input_amount: Decimal
    input_tax: Decimal
    input_invoice_count: int
    tax_payable: Decimal
    carried_forward: Decimal


class SurchargesCalculation(BaseModel):
    urban_maintenance_tax: Decimal
    education_surcharge: Decimal
    local_education_surcharge: Decimal
    total_surcharges: Decimal


class CorporateIncomeTax(BaseModel):
    total_revenue: Decimal
    total_deductions: Decimal
    prior_losses: Decimal
    taxable_income: Decimal
    tax_rate: Decimal
    tax_payable: Decimal


class TaxSummary(BaseModel):
    period: str
    vat: VATCalculation
    surcharges: SurchargesCalculation
    total_tax_burden: Decimal
