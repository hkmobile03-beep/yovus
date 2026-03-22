"""ROI优化引擎

核心功能：
- 多维度ROI追踪
- 转化归因分析
- 智能出价建议
- 投产比预测
"""

import pandas as pd
import numpy as np
from typing import Optional

from config import SystemConfig, DEFAULT_CONFIG, Platform
from models.campaign import Campaign, Keyword
from models.product import Product


class ROIOptimizer:
    """ROI优化器"""

    def __init__(self, campaigns: list[Campaign], products: list[Product],
                 config: SystemConfig = DEFAULT_CONFIG):
        self.campaigns = campaigns
        self.products = products
        self.config = config

    def get_roi_dashboard(self) -> dict:
        """多维度ROI总览"""
        # 按计划维度
        by_campaign = []
        for c in self.campaigns:
            cost = c.total_cost
            gmv = c.total_gmv
            by_campaign.append({
                "计划": c.name,
                "平台": c.platform.value,
                "花费": round(cost, 2),
                "成交额": round(gmv, 2),
                "ROI": round(c.roi, 2),
                "状态": "达标" if c.roi >= self.config.target_roi else "待优化",
            })

        # 按平台维度
        platform_data = {}
        for c in self.campaigns:
            pname = c.platform.value
            if pname not in platform_data:
                platform_data[pname] = {"cost": 0, "gmv": 0}
            platform_data[pname]["cost"] += c.total_cost
            platform_data[pname]["gmv"] += c.total_gmv

        by_platform = []
        for pname, data in platform_data.items():
            roi = data["gmv"] / data["cost"] if data["cost"] > 0 else 0
            by_platform.append({
                "平台": pname,
                "花费": round(data["cost"], 2),
                "成交额": round(data["gmv"], 2),
                "ROI": round(roi, 2),
            })

        # 汇总
        total_cost = sum(c.total_cost for c in self.campaigns)
        total_gmv = sum(c.total_gmv for c in self.campaigns)
        overall_roi = total_gmv / total_cost if total_cost > 0 else 0

        return {
            "整体ROI": round(overall_roi, 2),
            "目标ROI": self.config.target_roi,
            "按计划": by_campaign,
            "按平台": by_platform,
            "健康诊断": self._roi_health_check(overall_roi, by_campaign),
        }

    def _roi_health_check(self, overall_roi: float, by_campaign: list) -> dict:
        """ROI健康度诊断"""
        target = self.config.target_roi
        min_roi = self.config.min_acceptable_roi

        if overall_roi >= target * 1.3:
            health = "优秀"
            color = "green"
        elif overall_roi >= target:
            health = "良好"
            color = "blue"
        elif overall_roi >= min_roi:
            health = "一般"
            color = "yellow"
        else:
            health = "危险"
            color = "red"

        underperforming = [c for c in by_campaign if c["ROI"] < min_roi and c["花费"] > 0]
        excellent = [c for c in by_campaign if c["ROI"] >= target * 1.5 and c["花费"] > 0]

        return {
            "健康等级": health,
            "状态": color,
            "优秀计划数": len(excellent),
            "待优化计划数": len(underperforming),
            "建议": self._health_suggestions(health, overall_roi, underperforming),
        }

    def _health_suggestions(self, health: str, roi: float, underperforming: list) -> list[str]:
        """健康度建议"""
        suggestions = []
        target = self.config.target_roi

        if health == "危险":
            suggestions.append(f"整体ROI仅{roi:.2f}，远低于目标{target}，建议立即暂停低效计划止损")
            suggestions.append("重点排查：关键词质量分、人群精准度、创意点击率、商品竞争力")
        elif health == "一般":
            suggestions.append(f"ROI({roi:.2f})接近目标({target})，精细化优化可达标")
            if underperforming:
                names = [c["计划"] for c in underperforming]
                suggestions.append(f"重点优化: {', '.join(names)}")
        elif health == "良好":
            suggestions.append("ROI达标，可考虑适当放量测试更多流量")
        else:
            suggestions.append("ROI表现优秀，建议逐步提高预算扩大规模，同时监控ROI变化")

        return suggestions

    def get_bid_suggestions(self) -> list[dict]:
        """智能出价建议"""
        suggestions = []
        target_roi = self.config.target_roi

        for c in self.campaigns:
            for group in c.ad_groups:
                for kw in group.keywords:
                    if kw.clicks < 5:
                        continue  # 数据不足

                    suggestion = self._calc_bid_suggestion(kw, target_roi)
                    if suggestion:
                        suggestions.append(suggestion)

        # 按建议调整幅度排序
        suggestions.sort(key=lambda x: abs(x["调整幅度%"]), reverse=True)
        return suggestions[:30]  # 返回最需要调整的前30个

    def _calc_bid_suggestion(self, kw: Keyword, target_roi: float) -> Optional[dict]:
        """计算单个关键词出价建议"""
        current_bid = kw.bid
        current_roi = kw.roi
        cvr = kw.cvr / 100 if kw.cvr > 0 else 0

        if cvr == 0 or current_bid == 0:
            if kw.clicks >= 20 and kw.orders == 0:
                return {
                    "关键词": kw.keyword,
                    "当前出价": current_bid,
                    "当前ROI": round(current_roi, 2),
                    "建议出价": 0,
                    "调整幅度%": -100,
                    "操作": "建议暂停",
                    "原因": f"已有{kw.clicks}次点击但无转化",
                }
            return None

        # 基于目标ROI反推合理出价
        # ROI = GMV / Cost = (客单价 * 转化率 * 点击量) / (出价 * 点击量) = 客单价 * 转化率 / 出价
        avg_order_value = kw.gmv / kw.orders if kw.orders > 0 else 0
        if avg_order_value == 0:
            return None

        ideal_bid = avg_order_value * cvr / target_roi
        change_pct = (ideal_bid - current_bid) / current_bid * 100

        if abs(change_pct) < 5:
            return None  # 差异很小无需调整

        if change_pct > 0:
            action = f"提价至{ideal_bid:.2f}元"
        else:
            action = f"降价至{ideal_bid:.2f}元"

        return {
            "关键词": kw.keyword,
            "当前出价": current_bid,
            "当前ROI": round(current_roi, 2),
            "建议出价": round(ideal_bid, 2),
            "调整幅度%": round(change_pct, 1),
            "操作": action,
            "原因": f"目标ROI={target_roi}，当前ROI={current_roi:.2f}，客单价={avg_order_value:.0f}",
        }

    def get_roi_prediction(self, budget_change_pct: float = 0) -> dict:
        """ROI预测模型（基于历史数据线性预测）"""
        total_cost = sum(c.total_cost for c in self.campaigns)
        total_gmv = sum(c.total_gmv for c in self.campaigns)
        current_roi = total_gmv / total_cost if total_cost > 0 else 0

        # 简化预测：预算增加时ROI会有边际递减
        if budget_change_pct == 0:
            predicted_roi = current_roi
        elif budget_change_pct > 0:
            # 预算增加，ROI边际递减
            diminishing_factor = 1 - (budget_change_pct / 100 * 0.15)
            predicted_roi = current_roi * max(diminishing_factor, 0.5)
        else:
            # 预算减少（砍掉低效部分），ROI可能提升
            improvement_factor = 1 + (abs(budget_change_pct) / 100 * 0.1)
            predicted_roi = current_roi * min(improvement_factor, 1.5)

        new_budget = total_cost * (1 + budget_change_pct / 100)
        predicted_gmv = new_budget * predicted_roi

        return {
            "当前数据": {
                "日花费": round(total_cost, 2),
                "日成交": round(total_gmv, 2),
                "ROI": round(current_roi, 2),
            },
            "预算调整": f"{budget_change_pct:+.0f}%",
            "预测数据": {
                "预测日花费": round(new_budget, 2),
                "预测日成交": round(predicted_gmv, 2),
                "预测ROI": round(predicted_roi, 2),
            },
            "说明": "基于历史数据线性预测，实际效果受市场竞争、季节等因素影响",
            "场景分析": self._scenario_analysis(total_cost, current_roi),
        }

    def _scenario_analysis(self, current_cost: float, current_roi: float) -> list[dict]:
        """多场景预测"""
        scenarios = []
        for change in [-30, -10, 0, 10, 30, 50]:
            if change > 0:
                factor = 1 - (change / 100 * 0.15)
                pred_roi = current_roi * max(factor, 0.5)
            elif change < 0:
                factor = 1 + (abs(change) / 100 * 0.1)
                pred_roi = current_roi * min(factor, 1.5)
            else:
                pred_roi = current_roi

            new_cost = current_cost * (1 + change / 100)
            pred_gmv = new_cost * pred_roi

            scenarios.append({
                "预算调整": f"{change:+d}%",
                "预测花费": round(new_cost, 2),
                "预测成交": round(pred_gmv, 2),
                "预测ROI": round(pred_roi, 2),
                "达标": "是" if pred_roi >= self.config.target_roi else "否",
            })
        return scenarios

    def get_optimization_action_plan(self) -> dict:
        """生成综合优化行动计划"""
        total_cost = sum(c.total_cost for c in self.campaigns)
        total_gmv = sum(c.total_gmv for c in self.campaigns)
        current_roi = total_gmv / total_cost if total_cost > 0 else 0
        target = self.config.target_roi

        actions = {
            "immediate": [],   # 立即执行
            "short_term": [],  # 短期(1-3天)
            "medium_term": [], # 中期(1-2周)
        }

        # 立即执行项
        for c in self.campaigns:
            bad_kws = c.get_underperforming_keywords(min_clicks=15, max_roi=0.5)
            if bad_kws:
                kw_names = [kw.keyword for kw in bad_kws[:5]]
                actions["immediate"].append(
                    f"[{c.name}] 暂停{len(bad_kws)}个亏损关键词: {', '.join(kw_names)}"
                )

        if current_roi < self.config.min_acceptable_roi:
            actions["immediate"].append("整体ROI过低，建议暂停所有ROI<1的计划止损")

        # 短期优化
        actions["short_term"].extend([
            "优化低质量分关键词的创意相关性",
            "调整人群溢价，提高高转化人群出价",
            "检查并优化商品主图和详情页",
        ])

        # 中期优化
        actions["medium_term"].extend([
            "根据数据重新划分人群包，精细化运营",
            "测试新关键词扩展流量边界",
            "优化收藏加购到成交的转化链路",
            "建立定期数据复盘机制",
        ])

        return {
            "当前ROI": round(current_roi, 2),
            "目标ROI": target,
            "差距": round(target - current_roi, 2),
            "立即执行": actions["immediate"],
            "短期优化(1-3天)": actions["short_term"],
            "中期优化(1-2周)": actions["medium_term"],
            "预期效果": f"通过以上优化，预计可将ROI提升至{min(current_roi * 1.3, target * 1.1):.2f}",
        }
