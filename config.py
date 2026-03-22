"""淘宝营销分析系统 - 全局配置"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Platform(Enum):
    """投放平台"""
    ZHITONGCHE = "直通车"
    YINLIMOFA = "引力魔方"
    WANXIANGTAI = "万相台"


class CrowdLevel(Enum):
    """AIPL 人群阶段"""
    AWARENESS = "A-认知"
    INTEREST = "I-兴趣"
    PURCHASE = "P-购买"
    LOYALTY = "L-忠诚"


class ConsumptionTier(Enum):
    """消费层级"""
    LOW = "低消费"
    MEDIUM_LOW = "中低消费"
    MEDIUM = "中等消费"
    MEDIUM_HIGH = "中高消费"
    HIGH = "高消费"


class AgeGroup(Enum):
    """年龄段"""
    AGE_18_24 = "18-24岁"
    AGE_25_29 = "25-29岁"
    AGE_30_34 = "30-34岁"
    AGE_35_39 = "35-39岁"
    AGE_40_49 = "40-49岁"
    AGE_50_PLUS = "50岁以上"


class Gender(Enum):
    """性别"""
    MALE = "男"
    FEMALE = "女"


@dataclass
class SystemConfig:
    """系统配置"""
    # 店铺信息
    shop_name: str = "我的淘宝店铺"
    shop_category: str = "通用类目"

    # ROI 目标
    target_roi: float = 3.0
    min_acceptable_roi: float = 1.5

    # 预算设置
    daily_budget: float = 1000.0
    monthly_budget: float = 30000.0

    # 投放时段偏好 (0-23小时)
    peak_hours: list = field(default_factory=lambda: [9, 10, 11, 14, 15, 20, 21, 22])

    # 重点投放地域
    target_regions: list = field(default_factory=lambda: [
        "广东", "浙江", "江苏", "上海", "北京",
        "山东", "四川", "湖北", "福建", "河南"
    ])

    # 收藏加购转化周期 (天)
    fav_cart_conversion_window: int = 15

    # 报表输出路径
    report_output_dir: str = "./reports"


# 默认配置实例
DEFAULT_CONFIG = SystemConfig()
