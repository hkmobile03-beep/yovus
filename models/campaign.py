"""投放计划数据模型"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from config import Platform, CreativeType, PromotionType


@dataclass
class Keyword:
    """关键词"""
    keyword: str
    match_type: str = "广泛匹配"  # 广泛匹配/精准匹配
    bid: float = 0.0              # 出价
    quality_score: int = 6        # 质量分 (1-10)
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    orders: int = 0
    gmv: float = 0.0

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        return (self.orders / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def roi(self) -> float:
        return (self.gmv / self.cost) if self.cost > 0 else 0.0

    @property
    def ppc(self) -> float:
        return (self.cost / self.clicks) if self.clicks > 0 else 0.0


@dataclass
class AdGroup:
    """推广单元"""
    group_id: str
    name: str
    item_id: str
    keywords: list = field(default_factory=list)  # List[Keyword]
    crowd_ids: list = field(default_factory=list)  # 定向人群包ID
    bid_multiplier: float = 1.0  # 人群溢价比例
    status: str = "投放中"

    @property
    def total_cost(self) -> float:
        return sum(kw.cost for kw in self.keywords)

    @property
    def total_gmv(self) -> float:
        return sum(kw.gmv for kw in self.keywords)

    @property
    def roi(self) -> float:
        cost = self.total_cost
        return (self.total_gmv / cost) if cost > 0 else 0.0


@dataclass
class Campaign:
    """投放计划"""
    campaign_id: str
    name: str
    platform: Platform
    daily_budget: float
    start_date: date
    end_date: Optional[date] = None
    ad_groups: list = field(default_factory=list)  # List[AdGroup]
    target_regions: list = field(default_factory=list)
    schedule_hours: list = field(default_factory=list)  # 投放时段
    status: str = "投放中"
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_cost(self) -> float:
        return sum(g.total_cost for g in self.ad_groups)

    @property
    def total_gmv(self) -> float:
        return sum(g.total_gmv for g in self.ad_groups)

    @property
    def roi(self) -> float:
        cost = self.total_cost
        return (self.total_gmv / cost) if cost > 0 else 0.0

    @property
    def budget_utilization(self) -> float:
        """预算使用率"""
        return (self.total_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0.0

    def get_top_keywords(self, n: int = 10, by: str = "roi") -> list:
        """获取表现最好的关键词"""
        all_kws = []
        for group in self.ad_groups:
            all_kws.extend(group.keywords)
        return sorted(all_kws, key=lambda k: getattr(k, by, 0), reverse=True)[:n]

    def get_underperforming_keywords(self, min_clicks: int = 10, max_roi: float = 1.0) -> list:
        """获取表现不佳的关键词（需要优化或暂停）"""
        result = []
        for group in self.ad_groups:
            for kw in group.keywords:
                if kw.clicks >= min_clicks and kw.roi < max_roi:
                    result.append(kw)
        return result


@dataclass
class Creative:
    """创意素材"""
    creative_id: str
    name: str
    creative_type: CreativeType
    item_id: str
    impressions: int = 0
    clicks: int = 0
    favorites: int = 0
    cart_adds: int = 0
    orders: int = 0
    gmv: float = 0.0
    cost: float = 0.0
    # 落地页数据
    landing_page_views: int = 0
    bounce_count: int = 0         # 跳出次数
    avg_stay_seconds: float = 0.0  # 平均停留时长

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
    def bounce_rate(self) -> float:
        return (self.bounce_count / self.landing_page_views * 100) if self.landing_page_views > 0 else 0.0

    @property
    def roi(self) -> float:
        return (self.gmv / self.cost) if self.cost > 0 else 0.0


@dataclass
class Promotion:
    """促销活动"""
    promo_id: str
    name: str
    promo_type: PromotionType
    start_date: date
    end_date: date
    discount_value: float = 0.0     # 优惠力度(元或折扣)
    threshold: float = 0.0          # 门槛(满X元)
    # 活动效果
    impressions: int = 0
    participants: int = 0           # 参与人数
    orders: int = 0
    gmv: float = 0.0
    cost: float = 0.0               # 活动成本(优惠金额)
    new_customer_orders: int = 0    # 新客成交
    repeat_customer_orders: int = 0  # 老客成交

    @property
    def participation_rate(self) -> float:
        """参与率"""
        return (self.participants / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        """转化率(参与→下单)"""
        return (self.orders / self.participants * 100) if self.participants > 0 else 0.0

    @property
    def roi(self) -> float:
        """活动ROI(成交/优惠成本)"""
        return (self.gmv / self.cost) if self.cost > 0 else 0.0

    @property
    def avg_order_value(self) -> float:
        """客单价"""
        return (self.gmv / self.orders) if self.orders > 0 else 0.0

    @property
    def new_customer_ratio(self) -> float:
        """新客占比"""
        return (self.new_customer_orders / self.orders * 100) if self.orders > 0 else 0.0
