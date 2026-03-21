"""平台数据解析基类"""

from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd


class BasePlatformParser(ABC):
    """电商平台账单解析基类"""

    @abstractmethod
    def parse_orders(self, file_path: Path) -> list[dict[str, Any]]:
        """解析订单数据"""
        ...

    @abstractmethod
    def parse_settlement(self, file_path: Path) -> list[dict[str, Any]]:
        """解析结算账单"""
        ...

    @abstractmethod
    def parse_commission(self, file_path: Path) -> list[dict[str, Any]]:
        """解析佣金明细"""
        ...

    def _read_excel(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """读取Excel文件"""
        return pd.read_excel(file_path, **kwargs)

    def _read_csv(self, file_path: Path, encoding: str = "gbk", **kwargs) -> pd.DataFrame:
        """读取CSV文件（中国平台通常使用GBK编码）"""
        try:
            return pd.read_csv(file_path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="utf-8-sig", **kwargs)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """安全转换为Decimal"""
        if pd.isna(value) or value is None or value == "":
            return Decimal("0")
        return Decimal(str(value)).quantize(Decimal("0.01"))

    @staticmethod
    def _clean_order_no(order_no: Any) -> str:
        """清洗订单号（去除空格、引号等）"""
        return str(order_no).strip().strip("'\"= \t")
