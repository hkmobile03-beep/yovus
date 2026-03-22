"""人群分析引擎

核心功能：
- 消费者画像分析
- AIPL人群流转
- 人群价值评估
- 潜客挖掘建议
"""

import pandas as pd
import numpy as np
from collections import Counter
from typing import Optional

from config import CrowdLevel, ConsumptionTier, AgeGroup, Gender
from models.crowd import CrowdProfile, CrowdSegment


class CrowdAnalyzer:
    """人群分析器"""

    def __init__(self, profiles: list[CrowdProfile]):
        self.profiles = profiles
        self._df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        """将人群数据转为DataFrame便于分析"""
        records = []
        for p in self.profiles:
            records.append({
                "user_id": p.user_id,
                "age_group": p.age_group.value,
                "gender": p.gender.value,
                "region": p.region,
                "consumption_tier": p.consumption_tier.value,
                "crowd_level": p.crowd_level.value,
                "page_views": p.page_views,
                "favorites": p.favorites,
                "cart_adds": p.cart_adds,
                "purchases": p.purchases,
                "purchase_amount": p.purchase_amount,
                "last_visit_days": p.last_visit_days,
                "visit_frequency": p.visit_frequency,
                "engagement_score": p.engagement_score,
                "conversion_potential": p.conversion_potential,
            })
        return pd.DataFrame(records)

    def get_portrait_summary(self) -> dict:
        """获取整体人群画像概览"""
        df = self._df
        return {
            "总人数": len(df),
            "性别分布": df["gender"].value_counts().to_dict(),
            "年龄分布": df["age_group"].value_counts().to_dict(),
            "消费层级分布": df["consumption_tier"].value_counts().to_dict(),
            "地域TOP10": df["region"].value_counts().head(10).to_dict(),
            "AIPL分布": df["crowd_level"].value_counts().to_dict(),
            "平均互动分": round(df["engagement_score"].mean(), 2),
            "转化潜力分布": df["conversion_potential"].value_counts().to_dict(),
        }

    def get_aipl_analysis(self) -> dict:
        """AIPL人群流转分析"""
        df = self._df
        aipl_stats = {}
        for level in CrowdLevel:
            segment = df[df["crowd_level"] == level.value]
            if len(segment) == 0:
                continue
            aipl_stats[level.value] = {
                "人数": len(segment),
                "占比": f"{len(segment) / len(df) * 100:.1f}%",
                "平均互动分": round(segment["engagement_score"].mean(), 2),
                "平均消费金额": round(segment["purchase_amount"].mean(), 2),
                "高转化潜力占比": f"{(segment['conversion_potential'] == '高').sum() / len(segment) * 100:.1f}%",
            }

        # 流转建议
        suggestions = self._generate_aipl_suggestions(df)
        return {"AIPL分层数据": aipl_stats, "流转优化建议": suggestions}

    def _generate_aipl_suggestions(self, df: pd.DataFrame) -> list[str]:
        """基于AIPL数据生成优化建议"""
        suggestions = []
        total = len(df)
        if total == 0:
            return ["数据不足，无法生成建议"]

        a_count = len(df[df["crowd_level"] == CrowdLevel.AWARENESS.value])
        i_count = len(df[df["crowd_level"] == CrowdLevel.INTEREST.value])
        p_count = len(df[df["crowd_level"] == CrowdLevel.PURCHASE.value])
        l_count = len(df[df["crowd_level"] == CrowdLevel.LOYALTY.value])

        # A->I 转化分析
        if a_count > 0 and i_count / max(a_count, 1) < 0.3:
            suggestions.append(
                f"认知→兴趣转化率偏低({i_count}/{a_count}={i_count/a_count*100:.0f}%)，"
                "建议加大内容种草力度，通过短视频/直播/图文提升互动"
            )

        # I->P 转化分析
        if i_count > 0 and p_count / max(i_count, 1) < 0.2:
            suggestions.append(
                f"兴趣→购买转化率偏低({p_count}/{i_count}={p_count/i_count*100:.0f}%)，"
                "建议通过优惠券、限时折扣、加购有礼等活动促进转化"
            )

        # P->L 复购分析
        if p_count > 0 and l_count / max(p_count, 1) < 0.15:
            suggestions.append(
                f"购买→忠诚转化率偏低({l_count}/{p_count}={l_count/p_count*100:.0f}%)，"
                "建议加强会员体系建设，提供复购优惠和专属权益"
            )

        # 人群蓄水建议
        if a_count / max(total, 1) < 0.3:
            suggestions.append(
                "认知人群占比不足，建议通过引力魔方/万相台拉新，扩大人群蓄水池"
            )

        if not suggestions:
            suggestions.append("AIPL人群结构健康，建议保持当前运营策略并持续监测")

        return suggestions

    def get_high_value_segments(self, top_n: int = 5) -> list[dict]:
        """识别高价值人群分组"""
        df = self._df
        # 按 年龄+性别+消费层级 组合分析
        grouped = df.groupby(["age_group", "gender", "consumption_tier"]).agg(
            人数=("user_id", "count"),
            平均互动分=("engagement_score", "mean"),
            平均消费金额=("purchase_amount", "mean"),
            总消费金额=("purchase_amount", "sum"),
        ).reset_index()

        grouped["综合价值分"] = (
            grouped["平均互动分"] * 0.3
            + grouped["平均消费金额"].rank(pct=True) * 100 * 0.4
            + grouped["人数"].rank(pct=True) * 100 * 0.3
        )

        top_segments = grouped.nlargest(top_n, "综合价值分")
        results = []
        for _, row in top_segments.iterrows():
            results.append({
                "人群特征": f"{row['gender']}-{row['age_group']}-{row['consumption_tier']}",
                "人数": int(row["人数"]),
                "平均互动分": round(row["平均互动分"], 2),
                "平均消费金额": round(row["平均消费金额"], 2),
                "综合价值分": round(row["综合价值分"], 2),
            })
        return results

    def get_potential_customers(self, min_engagement: float = 30, max_purchases: int = 0) -> list[dict]:
        """潜客挖掘 - 高互动但未购买的人群"""
        df = self._df
        potentials = df[
            (df["engagement_score"] >= min_engagement) & (df["purchases"] <= max_purchases)
        ].sort_values("engagement_score", ascending=False)

        return {
            "潜客数量": len(potentials),
            "占总人群比例": f"{len(potentials) / len(df) * 100:.1f}%" if len(df) > 0 else "0%",
            "画像分布": {
                "性别": potentials["gender"].value_counts().to_dict(),
                "年龄": potentials["age_group"].value_counts().to_dict(),
                "消费层级": potentials["consumption_tier"].value_counts().to_dict(),
            },
            "建议触达方式": [
                "收藏加购人群定向投放，配合优惠券促转化",
                "通过短信/站内信推送新品或促销信息",
                "直播间引导关注加购，利用直播间氛围促成首单",
            ],
        }

    def get_region_analysis(self) -> dict:
        """地域分析"""
        df = self._df
        region_stats = df.groupby("region").agg(
            人数=("user_id", "count"),
            平均互动分=("engagement_score", "mean"),
            平均消费金额=("purchase_amount", "mean"),
            购买人数=("purchases", lambda x: (x > 0).sum()),
        ).reset_index()

        region_stats["转化率"] = (region_stats["购买人数"] / region_stats["人数"] * 100).round(2)
        region_stats = region_stats.sort_values("平均消费金额", ascending=False)

        return {
            "地域排行": region_stats.head(15).to_dict("records"),
            "建议": self._region_suggestions(region_stats),
        }

    def _region_suggestions(self, region_stats: pd.DataFrame) -> list[str]:
        """地域投放建议"""
        suggestions = []
        top_regions = region_stats.head(5)
        high_cvr = region_stats.nlargest(3, "转化率")

        suggestions.append(
            f"消费力TOP5地域: {', '.join(top_regions['region'].tolist())}，建议重点投放"
        )
        suggestions.append(
            f"转化率TOP3地域: {', '.join(high_cvr['region'].tolist())}，建议加大预算"
        )

        low_cvr = region_stats[region_stats["转化率"] < region_stats["转化率"].median() * 0.5]
        if len(low_cvr) > 0:
            suggestions.append(
                f"转化率偏低地域: {', '.join(low_cvr['region'].head(5).tolist())}，建议降低出价或暂停投放"
            )
        return suggestions
