"""广告投放计划分析引擎

核心功能：
- 投放计划效果总览
- 关键词分析与优化建议
- 人群定向分析
- 预算分配优化
- 投放时段策略
"""

import pandas as pd
import numpy as np
from typing import Optional

from config import Platform, SystemConfig, DEFAULT_CONFIG
from models.campaign import Campaign, AdGroup, Keyword


class CampaignAnalyzer:
    """投放计划分析器"""

    def __init__(self, campaigns: list[Campaign], config: SystemConfig = DEFAULT_CONFIG):
        self.campaigns = campaigns
        self.config = config

    def get_overview(self) -> dict:
        """投放计划效果总览"""
        results = []
        total_cost = 0
        total_gmv = 0

        for c in self.campaigns:
            cost = c.total_cost
            gmv = c.total_gmv
            total_cost += cost
            total_gmv += gmv

            results.append({
                "计划名称": c.name,
                "平台": c.platform.value,
                "日预算": c.daily_budget,
                "花费": round(cost, 2),
                "成交金额": round(gmv, 2),
                "ROI": round(c.roi, 2),
                "预算使用率": f"{c.budget_utilization:.1f}%",
                "状态": c.status,
                "单元数": len(c.ad_groups),
            })

        overall_roi = total_gmv / total_cost if total_cost > 0 else 0
        target_roi = self.config.target_roi

        return {
            "计划列表": results,
            "汇总": {
                "总花费": round(total_cost, 2),
                "总成交": round(total_gmv, 2),
                "整体ROI": round(overall_roi, 2),
                "目标ROI": target_roi,
                "ROI达成": "达标" if overall_roi >= target_roi else "未达标",
                "差距": round(overall_roi - target_roi, 2),
            },
            "优化建议": self._generate_overview_suggestions(results, overall_roi),
        }

    def _generate_overview_suggestions(self, results: list, overall_roi: float) -> list[str]:
        """生成投放总览优化建议"""
        suggestions = []
        target = self.config.target_roi

        if overall_roi < target:
            suggestions.append(
                f"整体ROI({overall_roi:.2f})未达目标({target})，需优化低效计划"
            )

        # 找出ROI低的计划
        low_roi = [r for r in results if r["ROI"] < self.config.min_acceptable_roi and r["花费"] > 0]
        if low_roi:
            names = [r["计划名称"] for r in low_roi]
            suggestions.append(f"以下计划ROI低于最低要求({self.config.min_acceptable_roi}): {', '.join(names)}")

        # 预算使用率分析
        low_budget = [r for r in results if float(r["预算使用率"].replace("%", "")) < 50]
        if low_budget:
            names = [r["计划名称"] for r in low_budget]
            suggestions.append(f"以下计划预算使用率不足50%: {', '.join(names)}，建议检查出价或关键词覆盖度")

        high_roi = [r for r in results if r["ROI"] > target * 1.5 and r["花费"] > 0]
        if high_roi:
            names = [r["计划名称"] for r in high_roi]
            suggestions.append(f"以下计划ROI优秀: {', '.join(names)}，建议提高预算扩大投放")

        return suggestions

    def analyze_keywords(self, campaign_id: Optional[str] = None) -> dict:
        """关键词分析"""
        campaigns = self.campaigns
        if campaign_id:
            campaigns = [c for c in campaigns if c.campaign_id == campaign_id]

        all_keywords = []
        for c in campaigns:
            for group in c.ad_groups:
                for kw in group.keywords:
                    all_keywords.append({
                        "关键词": kw.keyword,
                        "匹配方式": kw.match_type,
                        "出价": kw.bid,
                        "质量分": kw.quality_score,
                        "展现量": kw.impressions,
                        "点击量": kw.clicks,
                        "点击率": round(kw.ctr, 2),
                        "花费": round(kw.cost, 2),
                        "PPC": round(kw.ppc, 2),
                        "成交笔数": kw.orders,
                        "成交金额": round(kw.gmv, 2),
                        "ROI": round(kw.roi, 2),
                        "转化率": round(kw.cvr, 2),
                    })

        if not all_keywords:
            return {"error": "无关键词数据"}

        df = pd.DataFrame(all_keywords)

        # 分类
        high_roi_kws = df[df["ROI"] >= self.config.target_roi].nlargest(20, "成交金额")
        low_roi_kws = df[(df["ROI"] < self.config.min_acceptable_roi) & (df["点击量"] >= 10)]
        high_cost_kws = df.nlargest(10, "花费")
        low_quality_kws = df[df["质量分"] < 6]

        return {
            "关键词总数": len(df),
            "高ROI关键词TOP20": high_roi_kws.to_dict("records") if len(high_roi_kws) > 0 else [],
            "低效关键词(需优化)": low_roi_kws.to_dict("records") if len(low_roi_kws) > 0 else [],
            "高消耗关键词TOP10": high_cost_kws.to_dict("records"),
            "低质量分关键词": low_quality_kws.to_dict("records") if len(low_quality_kws) > 0 else [],
            "优化建议": self._keyword_suggestions(df),
        }

    def _keyword_suggestions(self, df: pd.DataFrame) -> list[str]:
        """关键词优化建议"""
        suggestions = []

        # 高花费低ROI关键词
        waste = df[(df["花费"] > df["花费"].median()) & (df["ROI"] < self.config.min_acceptable_roi)]
        if len(waste) > 0:
            total_waste = waste["花费"].sum()
            suggestions.append(
                f"有{len(waste)}个关键词高消耗低ROI，浪费花费约{total_waste:.0f}元，建议降价或暂停"
            )

        # 低质量分
        low_q = df[df["质量分"] < 6]
        if len(low_q) > 0:
            suggestions.append(
                f"有{len(low_q)}个关键词质量分低于6分，影响展现和PPC，建议优化创意相关性"
            )

        # 高CTR高CVR但出价低
        stars = df[(df["点击率"] > df["点击率"].quantile(0.75)) &
                   (df["转化率"] > df["转化率"].quantile(0.75))]
        if len(stars) > 0:
            suggestions.append(
                f"有{len(stars)}个关键词点击率和转化率双高，为优质词，建议适当提高出价争取更多展现"
            )

        return suggestions

    def get_budget_optimization(self) -> dict:
        """预算分配优化建议"""
        campaign_data = []
        for c in self.campaigns:
            if c.total_cost == 0:
                continue
            campaign_data.append({
                "campaign": c,
                "name": c.name,
                "platform": c.platform.value,
                "cost": c.total_cost,
                "gmv": c.total_gmv,
                "roi": c.roi,
                "budget": c.daily_budget,
            })

        if not campaign_data:
            return {"error": "无投放数据"}

        total_budget = self.config.daily_budget
        total_cost = sum(d["cost"] for d in campaign_data)

        # 按ROI加权分配预算
        suggestions = []
        reallocation = []

        for d in sorted(campaign_data, key=lambda x: x["roi"], reverse=True):
            roi = d["roi"]
            current_share = d["cost"] / total_cost * 100 if total_cost > 0 else 0
            target = self.config.target_roi

            if roi > target * 1.5:
                action = "增加预算30-50%"
                recommended = round(d["budget"] * 1.4, 0)
            elif roi > target:
                action = "维持或小幅增加10-20%"
                recommended = round(d["budget"] * 1.15, 0)
            elif roi > self.config.min_acceptable_roi:
                action = "优化关键词后维持"
                recommended = d["budget"]
            else:
                action = "降低预算50%或暂停优化"
                recommended = round(d["budget"] * 0.5, 0)

            reallocation.append({
                "计划": d["name"],
                "当前日预算": d["budget"],
                "当前ROI": round(roi, 2),
                "建议操作": action,
                "建议日预算": recommended,
            })

        return {
            "当前总日预算": total_budget,
            "预算分配建议": reallocation,
            "整体建议": [
                "将预算从低ROI计划转移至高ROI计划",
                "新计划建议从小预算测试开始，ROI达标后再逐步放量",
                f"单日总预算建议控制在{total_budget}元以内，待ROI稳定后再考虑放大",
            ],
        }

    def get_time_strategy(self) -> dict:
        """投放时段策略建议"""
        peak_hours = self.config.peak_hours
        return {
            "推荐投放时段": [f"{h}:00-{h+1}:00" for h in peak_hours],
            "分时段策略": {
                "高峰时段(9-11,14-15,20-22)": "提高出价20-30%，抢占优质流量",
                "平峰时段(12-13,16-19)": "维持正常出价",
                "低谷时段(0-8,23)": "降低出价30-50%或暂停投放，节省预算",
            },
            "建议": [
                "根据店铺实际成交数据调整时段出价",
                "大促期间(双11/618等)全时段提价",
                "测试期建议先全时段投放，积累数据后再优化",
            ],
        }
