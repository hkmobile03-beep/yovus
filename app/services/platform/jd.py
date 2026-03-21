"""京东平台数据解析"""

from decimal import Decimal
from pathlib import Path
from typing import Any

from app.services.platform.base import BasePlatformParser


class JDParser(BasePlatformParser):
    """京东账单解析

    京东结算周期：
    - 京东自营：月结，次月对账
    - 京东POP：T+1结算（货到付款T+7）

    费用构成：
    - 平台使用费（年费）
    - 扣点（佣金）= 订单金额 × 类目费率
    - 京东配送费（自营/使用京东物流时）
    """

    # 京东订单字段映射
    ORDER_FIELD_MAP = {
        "订单编号": "platform_order_no",
        "下单时间": "order_time",
        "完成时间": "complete_time",
        "订单状态": "status",
        "订单金额": "total_amount",
        "应付金额": "actual_payment",
        "商品名称": "product_name",
        "商品编号": "sku_code",
        "数量": "quantity",
        "单价": "unit_price",
        "优惠金额": "discount_amount",
        "运费": "freight_amount",
    }

    # 京东结算单字段映射
    SETTLEMENT_FIELD_MAP = {
        "结算单号": "settlement_no",
        "订单号": "order_no",
        "结算金额": "settlement_amount",
        "货款": "product_amount",
        "佣金": "commission_amount",
        "京东配送费": "delivery_fee",
        "退款金额": "refund_amount",
        "扣点费率": "commission_rate",
        "结算类型": "settlement_type",
        "结算周期": "settlement_period",
    }

    def parse_orders(self, file_path: Path) -> list[dict[str, Any]]:
        """解析京东订单导出"""
        df = self._read_excel(file_path)
        df.columns = df.columns.str.strip()

        orders = []
        for _, row in df.iterrows():
            order = {}
            for cn_field, en_field in self.ORDER_FIELD_MAP.items():
                if cn_field in df.columns:
                    order[en_field] = row.get(cn_field)

            for field in ["total_amount", "actual_payment", "discount_amount",
                          "freight_amount", "unit_price"]:
                if field in order:
                    order[field] = self._to_decimal(order[field])

            if "platform_order_no" in order:
                order["platform_order_no"] = self._clean_order_no(
                    order["platform_order_no"]
                )

            orders.append(order)

        return orders

    def parse_settlement(self, file_path: Path) -> list[dict[str, Any]]:
        """解析京东结算单

        京东POP结算 = 订单金额 - 佣金 - 京东配送费 - 退款
        京东自营结算 = 采购价 × 数量（月结）
        """
        df = self._read_excel(file_path)
        df.columns = df.columns.str.strip()

        records = []
        for _, row in df.iterrows():
            record = {}
            for cn_field, en_field in self.SETTLEMENT_FIELD_MAP.items():
                if cn_field in df.columns:
                    record[en_field] = row.get(cn_field)

            for field in ["settlement_amount", "product_amount", "commission_amount",
                          "delivery_fee", "refund_amount"]:
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

    def parse_commission(self, file_path: Path) -> list[dict[str, Any]]:
        """解析京东佣金明细"""
        return self.parse_settlement(file_path)

    @staticmethod
    def calculate_jd_pop_settlement(
        order_amount: Decimal,
        commission_rate: Decimal,
        delivery_fee: Decimal = Decimal("0"),
        refund_amount: Decimal = Decimal("0"),
    ) -> dict[str, Decimal]:
        """计算京东POP结算金额

        结算金额 = 订单金额 - 佣金 - 配送费 - 退款
        佣金 = 订单金额 × 类目扣点费率
        """
        commission = (order_amount * commission_rate).quantize(Decimal("0.01"))
        settlement = order_amount - commission - delivery_fee - refund_amount
        return {
            "commission": commission,
            "delivery_fee": delivery_fee,
            "settlement": settlement,
        }
