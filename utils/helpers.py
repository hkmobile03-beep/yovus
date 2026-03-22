"""通用工具函数"""

import json
from datetime import date, datetime


def format_currency(amount: float) -> str:
    """格式化金额"""
    return f"¥{amount:,.2f}"


def format_percentage(value: float) -> str:
    """格式化百分比"""
    return f"{value:.2f}%"


def date_range(start: date, end: date):
    """生成日期范围"""
    from datetime import timedelta
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


class DateEncoder(json.JSONEncoder):
    """JSON序列化支持date类型"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def save_json(data: dict, filepath: str):
    """保存JSON文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=DateEncoder)


def load_json(filepath: str) -> dict:
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
