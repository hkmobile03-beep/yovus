"""商品数据模型"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class ProductMetrics:
    """商品指标数据（日维度）"""
    date: date
    impressions: int = 0        # 展现量
    clicks: int = 0             # 点击量
    favorites: int = 0          # 收藏数
    cart_adds: int = 0          # 加购数
    orders: int = 0             # 成交笔数
    gmv: float = 0.0            # 成交金额
    cost: float = 0.0           # 花费
    visitors: int = 0           # 访客数

    @property
    def ctr(self) -> float:
        """点击率"""
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        """转化率 (点击->成交)"""
        return (self.orders / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def fav_cart_rate(self) -> float:
        """收藏加购率"""
        return ((self.favorites + self.cart_adds) / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def roi(self) -> float:
        """投入产出比"""
        return (self.gmv / self.cost) if self.cost > 0 else 0.0

    @property
    def ppc(self) -> float:
        """平均点击花费 (PPC)"""
        return (self.cost / self.clicks) if self.clicks > 0 else 0.0

    @property
    def uv_value(self) -> float:
        """UV价值"""
        return (self.gmv / self.visitors) if self.visitors > 0 else 0.0


@dataclass
class Product:
    """商品信息"""
    item_id: str
    title: str
    price: float
    category: str
    sku_count: int = 1
    daily_metrics: list = field(default_factory=list)  # List[ProductMetrics]

    @property
    def total_gmv(self) -> float:
        return sum(m.gmv for m in self.daily_metrics)

    @property
    def total_cost(self) -> float:
        return sum(m.cost for m in self.daily_metrics)

    @property
    def total_orders(self) -> int:
        return sum(m.orders for m in self.daily_metrics)

    @property
    def overall_roi(self) -> float:
        total_cost = self.total_cost
        return (self.total_gmv / total_cost) if total_cost > 0 else 0.0

    @property
    def total_favorites(self) -> int:
        return sum(m.favorites for m in self.daily_metrics)

    @property
    def total_cart_adds(self) -> int:
        return sum(m.cart_adds for m in self.daily_metrics)

    def get_metrics_range(self, start: date, end: date) -> list:
        """获取指定日期范围的指标"""
        return [m for m in self.daily_metrics if start <= m.date <= end]
