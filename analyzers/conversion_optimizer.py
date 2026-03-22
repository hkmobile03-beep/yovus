"""转化率优化引擎

针对淘宝/天猫广告投放的全链路转化率优化：
- 展现→点击 (CTR优化)
- 点击→收藏加购 (页面吸引力优化)
- 收藏加购→成交 (临门一脚转化)
- 落地页体验优化
- 人群×关键词×创意 交叉转化分析
- 竞争力诊断
"""

import pandas as pd
import numpy as np
from typing import Optional

from config import SystemConfig, DEFAULT_CONFIG, Platform
from models.campaign import Campaign, Keyword, Creative
from models.product import Product
from models.crowd import CrowdProfile


class ConversionOptimizer:
    """转化率优化器"""

    def __init__(self, campaigns: list[Campaign], products: list[Product],
                 creatives: Optional[list[Creative]] = None,
                 profiles: Optional[list[CrowdProfile]] = None,
                 config: SystemConfig = DEFAULT_CONFIG):
        self.campaigns = campaigns
        self.products = products
        self.creatives = creatives or []
        self.profiles = profiles or []
        self.config = config

    def get_full_funnel_diagnosis(self) -> dict:
        """全链路转化漏斗诊断"""
        # 汇总所有关键词数据
        total_imp = 0
        total_clicks = 0
        total_fav_cart = 0
        total_orders = 0
        total_gmv = 0.0
        total_cost = 0.0

        kw_data = []
        for c in self.campaigns:
            for g in c.ad_groups:
                for kw in g.keywords:
                    total_imp += kw.impressions
                    total_clicks += kw.clicks
                    total_orders += kw.orders
                    total_gmv += kw.gmv
                    total_cost += kw.cost
                    kw_data.append(kw)

        # 商品维度补充收藏加购
        for p in self.products:
            for m in p.daily_metrics:
                total_fav_cart += m.favorites + m.cart_adds

        ctr = total_clicks / total_imp * 100 if total_imp > 0 else 0
        fav_cart_rate = total_fav_cart / total_clicks * 100 if total_clicks > 0 else 0
        click_cvr = total_orders / total_clicks * 100 if total_clicks > 0 else 0
        fav_cart_cvr = total_orders / total_fav_cart * 100 if total_fav_cart > 0 else 0

        t_ctr = self.config.target_ctr
        t_cvr = self.config.target_cvr
        t_fcr = self.config.target_fav_cart_rate

        funnel = {
            "展现量": total_imp,
            "点击量": total_clicks,
            "点击率(CTR)": f"{ctr:.2f}%",
            "CTR目标": f"{t_ctr}%",
            "CTR状态": "达标" if ctr >= t_ctr else "待优化",
            "收藏加购量": total_fav_cart,
            "收藏加购率": f"{fav_cart_rate:.2f}%",
            "收藏加购率目标": f"{t_fcr}%",
            "收藏加购率状态": "达标" if fav_cart_rate >= t_fcr else "待优化",
            "成交笔数": total_orders,
            "点击转化率(CVR)": f"{click_cvr:.2f}%",
            "CVR目标": f"{t_cvr}%",
            "CVR状态": "达标" if click_cvr >= t_cvr else "待优化",
            "收藏加购→成交率": f"{fav_cart_cvr:.2f}%",
            "成交金额": round(total_gmv, 2),
            "总花费": round(total_cost, 2),
            "ROI": round(total_gmv / total_cost, 2) if total_cost > 0 else 0,
        }

        # 找到最大瓶颈
        gaps = []
        if ctr < t_ctr:
            gaps.append(("CTR(点击率)", t_ctr - ctr, self._ctr_optimization()))
        if fav_cart_rate < t_fcr:
            gaps.append(("收藏加购率", t_fcr - fav_cart_rate, self._fav_cart_rate_optimization()))
        if click_cvr < t_cvr:
            gaps.append(("CVR(转化率)", t_cvr - click_cvr, self._cvr_optimization()))

        if gaps:
            gaps.sort(key=lambda x: x[1], reverse=True)
            primary_bottleneck = gaps[0]
            funnel["最大瓶颈"] = primary_bottleneck[0]
            funnel["瓶颈差距"] = f"{primary_bottleneck[1]:.2f}个百分点"
            funnel["瓶颈优化方案"] = primary_bottleneck[2]
        else:
            funnel["最大瓶颈"] = "无 - 各环节均达标"

        # 各环节优化建议汇总
        funnel["分环节优化建议"] = {
            "展现→点击(CTR)": self._ctr_optimization(),
            "点击→收藏加购": self._fav_cart_rate_optimization(),
            "收藏加购→成交(CVR)": self._cvr_optimization(),
        }

        return funnel

    def _ctr_optimization(self) -> list[str]:
        """CTR优化建议"""
        return [
            "主图优化: 使用差异化卖点主图，避免同质化，突出价格/赠品/限时等利益点",
            "标题优化: 前14个字包含核心成交词，匹配搜索意图，提升关键词相关性",
            "人群精准度: 排除不相关人群，提高展现精准性，减少无效展现",
            "关键词优化: 删除CTR低于1%的宽泛词，保留精准长尾词",
            "创意轮播: 开启创意轮播测试，保留CTR最高的创意",
            "竞品差异化: 分析竞品主图策略，做差异化卖点呈现",
        ]

    def _fav_cart_rate_optimization(self) -> list[str]:
        """收藏加购率优化建议"""
        return [
            "详情页首屏: 3秒内传达核心卖点，放置收藏加购引导",
            "收藏加购有礼: 设置收藏领券/加购抽奖等互动，直接提升收藏加购率",
            "价格锚点: 通过划线价、到手价对比创造价值感",
            "SKU策略: 设置引流SKU低价拉收藏加购，主推SKU保利润",
            "买家秀/评价: 详情页嵌入优质买家秀和好评截图增强信任",
            "视频展示: 添加商品短视频展示使用效果，提升停留和互动",
        ]

    def _cvr_optimization(self) -> list[str]:
        """CVR(成交转化率)优化建议"""
        return [
            "催付策略: 对加购未下单人群发送催付短信/旺旺消息，配合限时优惠",
            "价格竞争力: 对比同行价格，确保到手价有竞争力",
            "满减凑单: 设置满减活动引导凑单，提高客单价和转化率",
            "限时活动: 创建倒计时紧迫感，设置前N件特价或限时折扣",
            "信任背书: 强化品牌背书、正品保障、运费险等消除购买顾虑",
            "客服转化: 优化自动回复话术，设置下单引导和异议处理FAQ",
            "支付优化: 开通花呗分期免息，降低支付门槛",
        ]

    def get_keyword_conversion_matrix(self) -> dict:
        """关键词转化矩阵分析 - 识别各关键词在漏斗各环节的表现"""
        rows = []
        for c in self.campaigns:
            for g in c.ad_groups:
                for kw in g.keywords:
                    if kw.clicks < 5:
                        continue
                    ctr = kw.ctr
                    cvr = kw.cvr
                    t_ctr = self.config.target_ctr
                    t_cvr = self.config.target_cvr

                    # 四象限分类
                    if ctr >= t_ctr and cvr >= t_cvr:
                        quadrant = "明星词(高点击高转化)"
                    elif ctr >= t_ctr and cvr < t_cvr:
                        quadrant = "引流词(高点击低转化)"
                    elif ctr < t_ctr and cvr >= t_cvr:
                        quadrant = "潜力词(低点击高转化)"
                    else:
                        quadrant = "待优化词(低点击低转化)"

                    rows.append({
                        "关键词": kw.keyword,
                        "计划": c.name,
                        "展现": kw.impressions,
                        "点击": kw.clicks,
                        "CTR%": round(ctr, 2),
                        "成交": kw.orders,
                        "CVR%": round(cvr, 2),
                        "花费": round(kw.cost, 2),
                        "ROI": round(kw.roi, 2),
                        "分类": quadrant,
                    })

        if not rows:
            return {"error": "无足够关键词数据"}

        df = pd.DataFrame(rows)
        quadrant_counts = df["分类"].value_counts().to_dict()

        # 各象限策略
        strategies = {
            "明星词(高点击高转化)": {
                "数量": quadrant_counts.get("明星词(高点击高转化)", 0),
                "策略": "加大出价抢排名，提高预算占比，这是核心盈利词",
                "关键词": df[df["分类"] == "明星词(高点击高转化)"].nlargest(10, "ROI")[["关键词", "CTR%", "CVR%", "ROI"]].to_dict("records"),
            },
            "引流词(高点击低转化)": {
                "数量": quadrant_counts.get("引流词(高点击低转化)", 0),
                "策略": "检查搜索意图匹配度，优化落地页与关键词的相关性，考虑调整匹配方式为精准匹配",
                "关键词": df[df["分类"] == "引流词(高点击低转化)"].nlargest(10, "花费")[["关键词", "CTR%", "CVR%", "ROI"]].to_dict("records"),
            },
            "潜力词(低点击高转化)": {
                "数量": quadrant_counts.get("潜力词(低点击高转化)", 0),
                "策略": "适当提高出价争取更多展现，优化创意标题提升点击率",
                "关键词": df[df["分类"] == "潜力词(低点击高转化)"].nlargest(10, "CVR%")[["关键词", "CTR%", "CVR%", "ROI"]].to_dict("records"),
            },
            "待优化词(低点击低转化)": {
                "数量": quadrant_counts.get("待优化词(低点击低转化)", 0),
                "策略": "花费高的考虑暂停，花费低的可保留观察，优先处理其他象限",
                "关键词": df[df["分类"] == "待优化词(低点击低转化)"].nlargest(10, "花费")[["关键词", "CTR%", "CVR%", "ROI"]].to_dict("records"),
            },
        }

        return {
            "关键词总数": len(df),
            "四象限分布": quadrant_counts,
            "四象限策略": strategies,
        }

    def get_creative_ab_analysis(self) -> dict:
        """创意素材A/B测试分析"""
        if not self.creatives:
            return {"error": "无创意数据"}

        rows = []
        for c in self.creatives:
            rows.append({
                "创意ID": c.creative_id,
                "名称": c.name,
                "类型": c.creative_type.value,
                "展现": c.impressions,
                "点击": c.clicks,
                "CTR%": round(c.ctr, 2),
                "收藏加购率%": round(c.fav_cart_rate, 2),
                "成交": c.orders,
                "CVR%": round(c.cvr, 2),
                "花费": round(c.cost, 2),
                "ROI": round(c.roi, 2),
                "跳出率%": round(c.bounce_rate, 2),
                "停留时长(秒)": round(c.avg_stay_seconds, 1),
            })

        df = pd.DataFrame(rows)

        # 按类型分组对比
        type_comparison = df.groupby("类型").agg(
            数量=("创意ID", "count"),
            平均CTR=("CTR%", "mean"),
            平均CVR=("CVR%", "mean"),
            平均收藏加购率=("收藏加购率%", "mean"),
            平均ROI=("ROI", "mean"),
            平均跳出率=("跳出率%", "mean"),
            平均停留时长=("停留时长(秒)", "mean"),
        ).round(2).reset_index().to_dict("records")

        # 最佳创意
        best_by_ctr = df.nlargest(5, "CTR%")[["名称", "类型", "CTR%", "CVR%", "ROI"]].to_dict("records")
        best_by_cvr = df.nlargest(5, "CVR%")[["名称", "类型", "CTR%", "CVR%", "ROI"]].to_dict("records")

        # 需要淘汰的创意
        poor_creatives = df[(df["CTR%"] < df["CTR%"].quantile(0.25)) &
                           (df["展现"] > df["展现"].median())]

        # 落地页诊断
        high_bounce = df[df["跳出率%"] > self.config.bounce_rate_warning]
        landing_diagnosis = []
        if len(high_bounce) > 0:
            for _, row in high_bounce.iterrows():
                landing_diagnosis.append(
                    f"[{row['名称']}] 跳出率{row['跳出率%']}%过高，停留仅{row['停留时长(秒)']}秒"
                )

        return {
            "创意总数": len(df),
            "按类型对比": type_comparison,
            "CTR最高创意TOP5": best_by_ctr,
            "CVR最高创意TOP5": best_by_cvr,
            "建议淘汰创意": poor_creatives[["名称", "类型", "CTR%", "CVR%"]].to_dict("records") if len(poor_creatives) > 0 else [],
            "落地页诊断": landing_diagnosis if landing_diagnosis else ["各创意落地页跳出率正常"],
            "优化建议": self._creative_suggestions(df),
        }

    def _creative_suggestions(self, df: pd.DataFrame) -> list[str]:
        """创意优化建议"""
        suggestions = []

        # 检查是否有视频类创意
        has_video = any(df["类型"] == "短视频")
        if not has_video:
            suggestions.append("建议新增短视频创意，视频素材通常比图片CTR高30-50%")

        # CTR差距分析
        ctr_range = df["CTR%"].max() - df["CTR%"].min()
        if ctr_range > 3:
            suggestions.append(
                f"创意间CTR差距达{ctr_range:.1f}个百分点，应淘汰低效创意，集中预算给高效创意"
            )

        # 跳出率
        avg_bounce = df["跳出率%"].mean()
        if avg_bounce > 60:
            suggestions.append(
                f"平均跳出率{avg_bounce:.1f}%偏高，建议优化落地页首屏加载速度和卖点呈现"
            )

        # 停留时长
        avg_stay = df["停留时长(秒)"].mean()
        if avg_stay < 30:
            suggestions.append(
                f"平均停留{avg_stay:.0f}秒过短，详情页内容吸引力不足，建议增加互动元素和卖点层次"
            )

        suggestions.append("每周至少测试2组新创意，保持创意迭代优化")
        return suggestions

    def get_promotion_conversion_analysis(self, promotions: list) -> dict:
        """促销活动转化分析"""
        if not promotions:
            return {"error": "无促销活动数据"}

        rows = []
        for p in promotions:
            rows.append({
                "活动名称": p.name,
                "活动类型": p.promo_type.value,
                "优惠力度": p.discount_value,
                "门槛": p.threshold,
                "参与人数": p.participants,
                "参与率%": round(p.participation_rate, 2),
                "成交笔数": p.orders,
                "转化率%": round(p.cvr, 2),
                "成交金额": round(p.gmv, 2),
                "活动成本": round(p.cost, 2),
                "活动ROI": round(p.roi, 2),
                "客单价": round(p.avg_order_value, 2),
                "新客占比%": round(p.new_customer_ratio, 2),
            })

        df = pd.DataFrame(rows)

        # 按活动类型汇总
        type_summary = df.groupby("活动类型").agg(
            活动数=("活动名称", "count"),
            总成交额=("成交金额", "sum"),
            总成本=("活动成本", "sum"),
            平均转化率=("转化率%", "mean"),
            平均客单价=("客单价", "mean"),
            平均新客占比=("新客占比%", "mean"),
        ).round(2)
        type_summary["整体ROI"] = (type_summary["总成交额"] / type_summary["总成本"]).round(2)
        type_summary = type_summary.reset_index().to_dict("records")

        # 效果排名
        best_roi = df.nlargest(5, "活动ROI")
        best_cvr = df.nlargest(5, "转化率%")

        return {
            "活动总数": len(df),
            "按类型汇总": type_summary,
            "ROI最高活动TOP5": best_roi[["活动名称", "活动类型", "转化率%", "活动ROI", "客单价"]].to_dict("records"),
            "转化率最高活动TOP5": best_cvr[["活动名称", "活动类型", "转化率%", "活动ROI", "客单价"]].to_dict("records"),
            "促销策略建议": self._promotion_suggestions(df),
        }

    def _promotion_suggestions(self, df: pd.DataFrame) -> list[str]:
        """促销策略建议"""
        suggestions = []

        # 高ROI活动类型
        type_roi = df.groupby("活动类型")["活动ROI"].mean().sort_values(ascending=False)
        if len(type_roi) > 0:
            best_type = type_roi.index[0]
            suggestions.append(f"ROI最高的活动类型是「{best_type}」(平均ROI={type_roi.iloc[0]:.1f})，建议作为常态化活动")

        # 新客获取
        high_new = df[df["新客占比%"] > 50]
        if len(high_new) > 0:
            suggestions.append(
                f"有{len(high_new)}个活动新客占比超50%，适合用于拉新场景，建议配合直通车新客人群包投放"
            )

        # 客单价分析
        avg_aov = df["客单价"].mean()
        high_aov = df[df["客单价"] > avg_aov * 1.3]
        if len(high_aov) > 0:
            suggestions.append(
                f"满减/套装类活动有效提升客单价(高于均值30%)，建议在大促期间主推"
            )

        suggestions.extend([
            "日常保持1-2个常态促销(如收藏领券)，大促叠加限时秒杀制造紧迫感",
            "新品期以买赠/试用装降低首购门槛，成熟期以满减提升客单价",
            "会员专享促销可提升复购率，建议每月1-2次会员日活动",
        ])

        return suggestions

    def get_platform_conversion_comparison(self) -> dict:
        """淘宝vs天猫各平台转化对比"""
        platform_data = {}
        for c in self.campaigns:
            pname = c.platform.value
            if pname not in platform_data:
                platform_data[pname] = {
                    "impressions": 0, "clicks": 0, "orders": 0,
                    "gmv": 0.0, "cost": 0.0,
                }
            for g in c.ad_groups:
                for kw in g.keywords:
                    platform_data[pname]["impressions"] += kw.impressions
                    platform_data[pname]["clicks"] += kw.clicks
                    platform_data[pname]["orders"] += kw.orders
                    platform_data[pname]["gmv"] += kw.gmv
                    platform_data[pname]["cost"] += kw.cost

        results = []
        for pname, d in platform_data.items():
            ctr = d["clicks"] / d["impressions"] * 100 if d["impressions"] > 0 else 0
            cvr = d["orders"] / d["clicks"] * 100 if d["clicks"] > 0 else 0
            roi = d["gmv"] / d["cost"] if d["cost"] > 0 else 0
            ppc = d["cost"] / d["clicks"] if d["clicks"] > 0 else 0

            results.append({
                "平台": pname,
                "展现": d["impressions"],
                "点击": d["clicks"],
                "CTR%": round(ctr, 2),
                "成交": d["orders"],
                "CVR%": round(cvr, 2),
                "PPC": round(ppc, 2),
                "花费": round(d["cost"], 2),
                "成交额": round(d["gmv"], 2),
                "ROI": round(roi, 2),
            })

        # 找最优平台
        if results:
            best_cvr = max(results, key=lambda x: x["CVR%"])
            best_roi = max(results, key=lambda x: x["ROI"])
            cross_suggestions = [
                f"转化率最高平台: {best_cvr['平台']}(CVR={best_cvr['CVR%']}%)，建议增加该平台预算",
                f"ROI最高平台: {best_roi['平台']}(ROI={best_roi['ROI']})，为最高效投放渠道",
            ]

            # 各平台特征建议
            for r in results:
                if r["CTR%"] > 5 and r["CVR%"] < 2:
                    cross_suggestions.append(
                        f"{r['平台']}: CTR高但CVR低，流量质量需关注，建议收紧人群或换精准匹配"
                    )
                if r["PPC"] > 3:
                    cross_suggestions.append(
                        f"{r['平台']}: PPC={r['PPC']}元偏高，建议优化质量分降低点击成本"
                    )
        else:
            cross_suggestions = []

        return {
            "平台对比": results,
            "跨平台策略": cross_suggestions,
        }

    def get_conversion_improvement_plan(self) -> dict:
        """生成系统化转化率提升方案"""
        funnel = self.get_full_funnel_diagnosis()

        plan = {
            "当前转化率水平": {
                "CTR": funnel["点击率(CTR)"],
                "收藏加购率": funnel["收藏加购率"],
                "CVR": funnel["点击转化率(CVR)"],
                "ROI": funnel["ROI"],
            },
            "第一阶段-止损(1-3天)": [
                "暂停ROI<1且花费>100元的关键词",
                "关闭CTR<1%且展现>500的创意",
                "排除不相关人群标签，收紧投放人群",
                "检查商品价格是否偏离市场竞争区间",
            ],
            "第二阶段-优化(3-7天)": [
                "根据四象限分析，对潜力词提高出价20%",
                "新增3组创意进行A/B测试",
                "优化详情页首屏，添加收藏加购引导",
                "设置催付短信，对加购3天未下单人群触达",
                "开启收藏加购有礼活动",
            ],
            "第三阶段-放量(7-14天)": [
                "对验证有效的关键词和创意加大预算",
                "拓展相似人群扩大流量池",
                "测试新促销活动形式提升转化",
                "优化投放时段和地域分配",
            ],
            "第四阶段-精细化(14-30天)": [
                "建立人群×关键词×创意的最优组合矩阵",
                "沉淀高转化人群包用于持续投放",
                "形成稳定的创意迭代测试机制",
                "建立日/周数据复盘和预警体系",
            ],
        }

        # 预估提升空间
        current_cvr = float(funnel["点击转化率(CVR)"].replace("%", ""))
        current_roi = funnel["ROI"]
        estimated_cvr = min(current_cvr * 1.5, self.config.target_cvr * 1.2)
        estimated_roi = current_roi * (estimated_cvr / current_cvr) if current_cvr > 0 else current_roi

        plan["预估效果"] = {
            "当前CVR": f"{current_cvr:.2f}%",
            "预估可优化至": f"{estimated_cvr:.2f}%",
            "CVR提升幅度": f"{(estimated_cvr / current_cvr - 1) * 100:.0f}%" if current_cvr > 0 else "N/A",
            "当前ROI": current_roi,
            "预估ROI": round(estimated_roi, 2),
            "说明": "基于各环节优化的综合预估，实际效果取决于执行力度和市场竞争",
        }

        return plan
