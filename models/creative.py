"""创意素材数据模型"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from config import CreativeType


@dataclass
class CreativeAsset:
    """创意素材"""
    creative_id: str
    item_id: str
    creative_type: CreativeType
    title: str
    # 投放数据
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    favorites: int = 0
    cart_adds: int = 0
    orders: int = 0
    gmv: float = 0.0
    # A/B测试分组
    test_group: str = ""  # "A" / "B" / ""

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        return (self.orders / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def fav_cart_rate(self) -> float:
        return ((self.favorites + self.cart_adds) / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def roi(self) -> float:
        return (self.gmv / self.cost) if self.cost > 0 else 0.0

    @property
    def ppc(self) -> float:
        return (self.cost / self.clicks) if self.clicks > 0 else 0.0


@dataclass
class LandingPage:
    """落地页/详情页数据"""
    page_id: str
    item_id: str
    page_type: str = "商品详情页"  # 商品详情页 / 活动页 / 店铺首页
    visitors: int = 0
    avg_stay_seconds: float = 0.0
    bounce_rate: float = 0.0    # 跳出率 %
    scroll_depth: float = 0.0   # 平均浏览深度 %
    favorites: int = 0
    cart_adds: int = 0
    orders: int = 0
    inquiries: int = 0          # 咨询量

    @property
    def fav_cart_rate(self) -> float:
        return ((self.favorites + self.cart_adds) / self.visitors * 100) if self.visitors > 0 else 0.0

    @property
    def cvr(self) -> float:
        return (self.orders / self.visitors * 100) if self.visitors > 0 else 0.0

    @property
    def inquiry_rate(self) -> float:
        """咨询率"""
        return (self.inquiries / self.visitors * 100) if self.visitors > 0 else 0.0


@dataclass
class Promotion:
    """促销活动"""
    promo_id: str
    name: str
    promo_type: str
    discount_value: str         # "满200减30" / "8折" / "买2送1"
    start_date: date
    end_date: date
    # 活动数据
    total_visitors: int = 0
    participants: int = 0       # 参与人数(领券/加入等)
    orders: int = 0
    gmv: float = 0.0
    cost: float = 0.0           # 促销成本(优惠券面额/赠品成本)
    new_customer_orders: int = 0  # 新客订单

    @property
    def participation_rate(self) -> float:
        """参与率"""
        return (self.participants / self.total_visitors * 100) if self.total_visitors > 0 else 0.0

    @property
    def cvr(self) -> float:
        """促销转化率"""
        return (self.orders / self.participants * 100) if self.participants > 0 else 0.0

    @property
    def promo_roi(self) -> float:
        """促销ROI (成交额/促销成本)"""
        return (self.gmv / self.cost) if self.cost > 0 else 0.0

    @property
    def avg_order_value(self) -> float:
        """客单价"""
        return (self.gmv / self.orders) if self.orders > 0 else 0.0

    @property
    def new_customer_rate(self) -> float:
        """拉新率"""
        return (self.new_customer_orders / self.orders * 100) if self.orders > 0 else 0.0
