"""天猫/淘宝平台数据解析"""

from decimal import Decimal
from pathlib import Path
from typing import Any

from app.services.platform.base import BasePlatformParser


class TmallParser(BasePlatformParser):
    """天猫/淘宝账单解析

    天猫结算周期：每月1日和16日结算
    淘宝结算：交易成功后实时结算到支付宝

    账单类型：
    - 已卖出的宝贝（订单数据）
    - 账务明细（支付宝流水）
    - 营销活动费用
    """

    # 天猫「已卖出的宝贝」字段映射
    ORDER_FIELD_MAP = {
        "订单编号": "platform_order_no",
        "买家会员名": "buyer_name",
        "买家实际支付金额": "actual_payment",
        "总金额": "total_amount",
        "退款金额": "refund_amount",
        "买家应付货款": "product_amount",
        "买家应付邮费": "freight_amount",
        "返点积分": "points_discount",
        "订单状态": "status",
        "订单创建时间": "order_time",
        "订单付款时间": "pay_time",
        "宝贝标题": "product_name",
        "宝贝种类": "product_type",
        "数量": "quantity",
        "物流单号": "tracking_no",
    }

    # 天猫账务明细字段映射
    SETTLEMENT_FIELD_MAP = {
        "业务流水号": "transaction_no",
        "商户订单号": "order_no",
        "入账时间": "settle_time",
        "收入（+元）": "income",
        "支出（-元）": "expense",
        "账户余额（元）": "balance",
        "交易对方": "counterparty",
        "业务类型": "business_type",
        "备注": "remark",
    }

    def parse_orders(self, file_path: Path) -> list[dict[str, Any]]:
        """解析天猫/淘宝已卖出的宝贝导出"""
        df = self._read_csv(file_path)

        # 清洗列名（去除空格）
        df.columns = df.columns.str.strip()

        orders = []
        for _, row in df.iterrows():
            order = {}
            for cn_field, en_field in self.ORDER_FIELD_MAP.items():
                if cn_field in df.columns:
                    order[en_field] = row.get(cn_field)

            # 转换金额字段
            for field in ["actual_payment", "total_amount", "refund_amount",
                          "product_amount", "freight_amount"]:
                if field in order:
                    order[field] = self._to_decimal(order[field])

            # 清洗订单号
            if "platform_order_no" in order:
                order["platform_order_no"] = self._clean_order_no(
                    order["platform_order_no"]
                )

            orders.append(order)

        return orders

    def parse_settlement(self, file_path: Path) -> list[dict[str, Any]]:
        """解析支付宝账务明细

        天猫结算流程：
        买家付款 → 平台托管 → 确认收货 → 扣除佣金/服务费 → 结算到支付宝
        """
        df = self._read_csv(file_path)
        df.columns = df.columns.str.strip()

        records = []
        for _, row in df.iterrows():
            record = {}
            for cn_field, en_field in self.SETTLEMENT_FIELD_MAP.items():
                if cn_field in df.columns:
                    record[en_field] = row.get(cn_field)

            record["income"] = self._to_decimal(record.get("income", 0))
            record["expense"] = self._to_decimal(record.get("expense", 0))
            record["balance"] = self._to_decimal(record.get("balance", 0))

            if "order_no" in record:
                record["order_no"] = self._clean_order_no(record["order_no"])

            records.append(record)

        return records

    def parse_commission(self, file_path: Path) -> list[dict[str, Any]]:
        """解析天猫佣金明细

        天猫佣金计算：
        佣金 = 实际成交金额 × 类目佣金费率
        技术服务费 = 年费（根据类目和销售额退还比例不同）
        """
        df = self._read_excel(file_path)
        df.columns = df.columns.str.strip()

        commission_field_map = {
            "订单编号": "order_no",
            "佣金金额": "commission_amount",
            "技术服务费": "tech_service_fee",
            "佣金比率": "commission_rate",
            "结算金额": "settlement_amount",
        }

        records = []
        for _, row in df.iterrows():
            record = {}
            for cn_field, en_field in commission_field_map.items():
                if cn_field in df.columns:
                    record[en_field] = row.get(cn_field)

            for field in ["commission_amount", "tech_service_fee", "settlement_amount"]:
                if field in record:
                    record[field] = self._to_decimal(record[field])

            if "commission_rate" in record:
                record["commission_rate"] = Decimal(
                    str(record["commission_rate"] or "0")
                )

            if "order_no" in record:
                record["order_no"] = self._clean_order_no(record["order_no"])

            records.append(record)

        return records

    @staticmethod
    def calculate_tmall_commission(
        amount: Decimal,
        commission_rate: Decimal,
    ) -> dict[str, Decimal]:
        """计算天猫佣金

        天猫佣金 = 实付金额(不含运费) × 类目佣金费率
        """
        commission = (amount * commission_rate).quantize(Decimal("0.01"))
        settlement = amount - commission
        return {
            "commission": commission,
            "settlement": settlement,
        }
