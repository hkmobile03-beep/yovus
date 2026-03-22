"""收藏加购数据分析引擎

核心功能：
- 收藏/加购趋势分析
- 转化漏斗分析
- 商品维度排行
- 收藏加购人群画像
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Optional

from models.product import Product, ProductMetrics
from models.crowd import CrowdProfile


class CartFavAnalyzer:
    """收藏加购分析器"""

    def __init__(self, products: list[Product], profiles: Optional[list[CrowdProfile]] = None):
        self.products = products
        self.profiles = profiles or []

    def get_trend_analysis(self, days: int = 30) -> dict:
        """收藏加购趋势分析"""
        daily_data = {}
        for product in self.products:
            for m in product.daily_metrics:
                d = str(m.date)
                if d not in daily_data:
                    daily_data[d] = {"favorites": 0, "cart_adds": 0, "orders": 0, "clicks": 0}
                daily_data[d]["favorites"] += m.favorites
                daily_data[d]["cart_adds"] += m.cart_adds
                daily_data[d]["orders"] += m.orders
                daily_data[d]["clicks"] += m.clicks

        df = pd.DataFrame.from_dict(daily_data, orient="index")
        if df.empty:
            return {"error": "无数据"}

        df.index = pd.to_datetime(df.index)
        df = df.sort_index().tail(days)

        df["fav_cart_total"] = df["favorites"] + df["cart_adds"]
        df["fav_cart_rate"] = (df["fav_cart_total"] / df["clicks"] * 100).round(2)
        df["fav_to_order_rate"] = (df["orders"] / df["fav_cart_total"].replace(0, np.nan) * 100).round(2)

        return {
            "日均收藏数": round(df["favorites"].mean(), 1),
            "日均加购数": round(df["cart_adds"].mean(), 1),
            "日均收藏加购率": f"{df['fav_cart_rate'].mean():.2f}%",
            "收藏加购→成交转化率": f"{df['fav_to_order_rate'].mean():.2f}%",
            "趋势数据": df[["favorites", "cart_adds", "fav_cart_total", "fav_cart_rate"]].to_dict("index"),
            "趋势诊断": self._diagnose_trend(df),
        }

    def _diagnose_trend(self, df: pd.DataFrame) -> list[str]:
        """诊断收藏加购趋势"""
        suggestions = []
        if len(df) < 7:
            return ["数据天数不足7天，暂无法做趋势诊断"]

        recent_7d = df.tail(7)["fav_cart_total"].mean()
        previous_7d = df.tail(14).head(7)["fav_cart_total"].mean() if len(df) >= 14 else recent_7d

        if previous_7d > 0:
            change = (recent_7d - previous_7d) / previous_7d * 100
            if change > 20:
                suggestions.append(f"近7天收藏加购量环比增长{change:.1f}%，势头良好，建议加大投放抢占流量")
            elif change < -20:
                suggestions.append(f"近7天收藏加购量环比下降{abs(change):.1f}%，建议检查主图/详情页/价格竞争力")
            else:
                suggestions.append(f"近7天收藏加购量环比变化{change:.1f}%，保持稳定")

        avg_rate = df["fav_cart_rate"].mean()
        if avg_rate < 8:
            suggestions.append(f"收藏加购率偏低({avg_rate:.1f}%)，行业优秀值约12-15%，建议优化商品卖点和详情页")
        elif avg_rate > 15:
            suggestions.append(f"收藏加购率优秀({avg_rate:.1f}%)，建议通过定向优惠促进转化下单")

        return suggestions

    def get_conversion_funnel(self) -> dict:
        """收藏加购转化漏斗"""
        total_impressions = 0
        total_clicks = 0
        total_favorites = 0
        total_cart_adds = 0
        total_orders = 0
        total_gmv = 0.0

        for product in self.products:
            for m in product.daily_metrics:
                total_impressions += m.impressions
                total_clicks += m.clicks
                total_favorites += m.favorites
                total_cart_adds += m.cart_adds
                total_orders += m.orders
                total_gmv += m.gmv

        fav_cart_total = total_favorites + total_cart_adds

        funnel = {
            "展现量": total_impressions,
            "点击量": total_clicks,
            "点击率": f"{total_clicks / total_impressions * 100:.2f}%" if total_impressions > 0 else "0%",
            "收藏数": total_favorites,
            "加购数": total_cart_adds,
            "收藏加购合计": fav_cart_total,
            "收藏加购率": f"{fav_cart_total / total_clicks * 100:.2f}%" if total_clicks > 0 else "0%",
            "成交笔数": total_orders,
            "收藏加购→成交转化率": f"{total_orders / fav_cart_total * 100:.2f}%" if fav_cart_total > 0 else "0%",
            "成交金额": round(total_gmv, 2),
        }

        # 漏斗瓶颈诊断
        funnel["瓶颈诊断"] = self._diagnose_funnel(
            total_impressions, total_clicks, fav_cart_total, total_orders
        )
        return funnel

    def _diagnose_funnel(self, impressions: int, clicks: int,
                          fav_cart: int, orders: int) -> list[str]:
        """漏斗瓶颈诊断"""
        diag = []
        ctr = clicks / impressions * 100 if impressions > 0 else 0
        fav_cart_rate = fav_cart / clicks * 100 if clicks > 0 else 0
        cvr = orders / fav_cart * 100 if fav_cart > 0 else 0

        if ctr < 3:
            diag.append(f"[展现→点击] 点击率{ctr:.1f}%偏低，建议优化主图创意、标题关键词")
        if fav_cart_rate < 8:
            diag.append(f"[点击→收藏加购] 收藏加购率{fav_cart_rate:.1f}%偏低，建议优化详情页、增加利益点")
        if cvr < 15:
            diag.append(f"[收藏加购→成交] 转化率{cvr:.1f}%偏低，建议通过催付短信、限时优惠、满减活动促转化")

        if not diag:
            diag.append("转化漏斗各环节表现良好")
        return diag

    def get_product_ranking(self, top_n: int = 20) -> list[dict]:
        """商品收藏加购排行"""
        rankings = []
        for product in self.products:
            total_fav = product.total_favorites
            total_cart = product.total_cart_adds
            total_orders = product.total_orders
            fav_cart = total_fav + total_cart

            rankings.append({
                "商品ID": product.item_id,
                "商品名称": product.title[:30],
                "价格": product.price,
                "收藏数": total_fav,
                "加购数": total_cart,
                "收藏加购合计": fav_cart,
                "成交笔数": total_orders,
                "收藏加购→成交率": f"{total_orders / fav_cart * 100:.1f}%" if fav_cart > 0 else "0%",
            })

        rankings.sort(key=lambda x: x["收藏加购合计"], reverse=True)
        return rankings[:top_n]

    def get_fav_cart_crowd_profile(self) -> dict:
        """收藏加购人群画像分析"""
        if not self.profiles:
            return {"error": "未提供人群数据"}

        # 筛选有收藏或加购行为的用户
        fav_cart_users = [p for p in self.profiles if p.favorites > 0 or p.cart_adds > 0]

        if not fav_cart_users:
            return {"error": "无收藏加购用户"}

        df = pd.DataFrame([{
            "gender": p.gender.value,
            "age_group": p.age_group.value,
            "consumption_tier": p.consumption_tier.value,
            "region": p.region,
            "favorites": p.favorites,
            "cart_adds": p.cart_adds,
            "purchases": p.purchases,
            "engagement_score": p.engagement_score,
        } for p in fav_cart_users])

        converted = df[df["purchases"] > 0]

        return {
            "收藏加购人数": len(df),
            "已转化人数": len(converted),
            "转化率": f"{len(converted) / len(df) * 100:.1f}%",
            "性别分布": df["gender"].value_counts().to_dict(),
            "年龄分布": df["age_group"].value_counts().to_dict(),
            "消费层级": df["consumption_tier"].value_counts().to_dict(),
            "地域TOP10": df["region"].value_counts().head(10).to_dict(),
            "建议": [
                "对收藏未加购人群推送加购有礼活动",
                "对加购未下单人群推送限时优惠券",
                "高价值收藏加购人群建立专属人群包用于投放",
            ],
        }
