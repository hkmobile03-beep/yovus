"""人群数据模型"""

from dataclasses import dataclass, field
from typing import Optional
from config import CrowdLevel, ConsumptionTier, AgeGroup, Gender


@dataclass
class CrowdProfile:
    """消费者画像"""
    user_id: str
    age_group: AgeGroup
    gender: Gender
    region: str
    consumption_tier: ConsumptionTier
    crowd_level: CrowdLevel
    # 行为数据
    page_views: int = 0
    favorites: int = 0
    cart_adds: int = 0
    purchases: int = 0
    purchase_amount: float = 0.0
    last_visit_days: int = 0  # 距离上次访问天数
    visit_frequency: int = 0  # 近30天访问次数

    @property
    def engagement_score(self) -> float:
        """用户互动评分 (0-100)"""
        score = 0.0
        score += min(self.page_views * 2, 20)
        score += min(self.favorites * 5, 15)
        score += min(self.cart_adds * 8, 20)
        score += min(self.purchases * 15, 30)
        score += min(self.visit_frequency * 1.5, 15)
        return min(score, 100.0)

    @property
    def conversion_potential(self) -> str:
        """转化潜力评级"""
        score = self.engagement_score
        if score >= 70:
            return "高"
        elif score >= 40:
            return "中"
        else:
            return "低"


@dataclass
class CrowdSegment:
    """人群分组/人群包"""
    segment_id: str
    name: str
    description: str
    profiles: list = field(default_factory=list)
    crowd_level: Optional[CrowdLevel] = None

    @property
    def size(self) -> int:
        return len(self.profiles)

    @property
    def avg_engagement(self) -> float:
        if not self.profiles:
            return 0.0
        return sum(p.engagement_score for p in self.profiles) / len(self.profiles)

    def filter_by_age(self, age_group: AgeGroup) -> list:
        return [p for p in self.profiles if p.age_group == age_group]

    def filter_by_gender(self, gender: Gender) -> list:
        return [p for p in self.profiles if p.gender == gender]

    def filter_by_region(self, region: str) -> list:
        return [p for p in self.profiles if p.region == region]

    def filter_by_consumption(self, tier: ConsumptionTier) -> list:
        return [p for p in self.profiles if p.consumption_tier == tier]

    def get_crowd_distribution(self) -> dict:
        """获取AIPL人群分布"""
        dist = {}
        for level in CrowdLevel:
            count = len([p for p in self.profiles if p.crowd_level == level])
            dist[level.value] = count
        return dist
