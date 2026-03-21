"""税务计算单元测试"""

from decimal import Decimal

import pytest

from app.services.budget_service import BudgetService


class TestVATCalculation:
    """增值税计算测试"""

    def test_price_tax_separation(self):
        """测试价税分离（一般纳税人13%）"""
        inc_tax = Decimal("1130")  # 含税价
        tax_rate = Decimal("0.13")
        ex_tax = (inc_tax / (1 + tax_rate)).quantize(Decimal("0.01"))
        vat = inc_tax - ex_tax

        assert ex_tax == Decimal("1000.00")
        assert vat == Decimal("130.00")

    def test_price_tax_separation_9_percent(self):
        """测试9%税率价税分离"""
        inc_tax = Decimal("1090")
        tax_rate = Decimal("0.09")
        ex_tax = (inc_tax / (1 + tax_rate)).quantize(Decimal("0.01"))
        vat = inc_tax - ex_tax

        assert ex_tax == Decimal("1000.00")
        assert vat == Decimal("90.00")

    def test_surcharges_calculation(self):
        """测试附加税计算"""
        vat_payable = Decimal("10000")

        urban_tax = (vat_payable * Decimal("0.07")).quantize(Decimal("0.01"))
        edu_surcharge = (vat_payable * Decimal("0.03")).quantize(Decimal("0.01"))
        local_edu = (vat_payable * Decimal("0.02")).quantize(Decimal("0.01"))

        assert urban_tax == Decimal("700.00")
        assert edu_surcharge == Decimal("300.00")
        assert local_edu == Decimal("200.00")
        assert urban_tax + edu_surcharge + local_edu == Decimal("1200.00")


class TestCorporateIncomeTax:
    """企业所得税计算测试"""

    def test_small_profit_enterprise_under_100w(self):
        """小型微利企业 应纳税所得额≤100万 实际税率5%"""
        taxable_income = Decimal("800000")
        tax = (taxable_income * Decimal("0.05")).quantize(Decimal("0.01"))
        assert tax == Decimal("40000.00")

    def test_small_profit_enterprise_under_300w(self):
        """小型微利企业 100万<应纳税所得额≤300万 实际税率10%"""
        taxable_income = Decimal("2000000")
        tax = (taxable_income * Decimal("0.10")).quantize(Decimal("0.01"))
        assert tax == Decimal("200000.00")

    def test_standard_rate(self):
        """标准税率25%"""
        taxable_income = Decimal("5000000")
        tax = (taxable_income * Decimal("0.25")).quantize(Decimal("0.01"))
        assert tax == Decimal("1250000.00")


class TestCommissionCalculation:
    """佣金计算测试"""

    def test_tmall_commission(self):
        """天猫佣金计算"""
        from app.services.platform.tmall import TmallParser

        result = TmallParser.calculate_tmall_commission(
            amount=Decimal("1000"),
            commission_rate=Decimal("0.05"),
        )
        assert result["commission"] == Decimal("50.00")
        assert result["settlement"] == Decimal("950.00")

    def test_jd_pop_settlement(self):
        """京东POP结算计算"""
        from app.services.platform.jd import JDParser

        result = JDParser.calculate_jd_pop_settlement(
            order_amount=Decimal("1000"),
            commission_rate=Decimal("0.08"),
            delivery_fee=Decimal("10"),
            refund_amount=Decimal("0"),
        )
        assert result["commission"] == Decimal("80.00")
        assert result["delivery_fee"] == Decimal("10")
        assert result["settlement"] == Decimal("910.00")


class TestBudgetEvaluation:
    """预算评估测试"""

    def test_alert_rule_evaluation(self):
        """预警规则评估"""
        assert BudgetService._evaluate_rule(
            Decimal("25"), "gt", Decimal("20")
        ) is True
        assert BudgetService._evaluate_rule(
            Decimal("15"), "gt", Decimal("20")
        ) is False
        assert BudgetService._evaluate_rule(
            Decimal("10"), "lt", Decimal("20")
        ) is True
        assert BudgetService._evaluate_rule(
            Decimal("20"), "eq", Decimal("20")
        ) is True
