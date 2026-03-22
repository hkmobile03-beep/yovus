#!/usr/bin/env python3
"""
淘宝营销分析系统 - 主入口

功能：
  1. 人群画像分析 & AIPL流转
  2. 收藏加购数据分析
  3. 广告投放计划分析
  4. ROI优化与出价建议
  5. 导出HTML分析报告

使用方法：
  python main.py              # 运行完整分析
  python main.py --module crowd    # 仅人群分析
  python main.py --module cart     # 仅收藏加购分析
  python main.py --module campaign # 仅投放分析
  python main.py --module roi      # 仅ROI优化
  python main.py --export          # 导出HTML报告
"""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel

from config import DEFAULT_CONFIG
from data.sample_generator import generate_all_sample_data
from analyzers.crowd_analyzer import CrowdAnalyzer
from analyzers.cart_fav_analyzer import CartFavAnalyzer
from analyzers.campaign_analyzer import CampaignAnalyzer
from analyzers.roi_optimizer import ROIOptimizer
from dashboard.reporter import Reporter

console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════════════╗
║          淘宝营销分析系统 v1.0                    ║
║    Taobao Marketing Analytics System             ║
║                                                  ║
║  人群分析 | 收藏加购 | 广告投放 | ROI优化         ║
╚══════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold red")


def run_crowd_analysis(profiles, reporter) -> dict:
    """运行人群分析"""
    console.print("\n[bold]━━━ 模块一：人群画像分析 ━━━[/bold]", style="magenta")

    analyzer = CrowdAnalyzer(profiles)

    # 1. 整体画像
    portrait = analyzer.get_portrait_summary()
    reporter.print_section("人群画像概览", portrait)

    # 2. AIPL分析
    aipl = analyzer.get_aipl_analysis()
    reporter.print_section("AIPL人群流转分析", aipl)

    # 3. 高价值人群
    high_value = analyzer.get_high_value_segments(top_n=5)
    reporter.print_section("高价值人群TOP5", high_value)

    # 4. 潜客挖掘
    potentials = analyzer.get_potential_customers()
    reporter.print_section("潜客挖掘", potentials)

    # 5. 地域分析
    region = analyzer.get_region_analysis()
    reporter.print_section("地域分析", region)

    return {
        "人群画像概览": portrait,
        "AIPL分析": aipl,
        "高价值人群": high_value,
        "潜客挖掘": potentials,
        "地域分析": region,
    }


def run_cart_fav_analysis(products, profiles, reporter) -> dict:
    """运行收藏加购分析"""
    console.print("\n[bold]━━━ 模块二：收藏加购分析 ━━━[/bold]", style="magenta")

    analyzer = CartFavAnalyzer(products, profiles)

    # 1. 趋势分析
    trend = analyzer.get_trend_analysis(days=30)
    trend_display = {k: v for k, v in trend.items() if k != "趋势数据"}
    reporter.print_section("收藏加购趋势(近30天)", trend_display)

    # 2. 转化漏斗
    funnel = analyzer.get_conversion_funnel()
    reporter.print_funnel(funnel)

    # 3. 商品排行
    ranking = analyzer.get_product_ranking(top_n=10)
    reporter.print_section("商品收藏加购排行TOP10", ranking)

    # 4. 收藏加购人群画像
    crowd = analyzer.get_fav_cart_crowd_profile()
    reporter.print_section("收藏加购人群画像", crowd)

    return {
        "趋势分析": trend_display,
        "转化漏斗": funnel,
        "商品排行": ranking,
        "人群画像": crowd,
    }


def run_campaign_analysis(campaigns, reporter) -> dict:
    """运行投放分析"""
    console.print("\n[bold]━━━ 模块三：广告投放分析 ━━━[/bold]", style="magenta")

    analyzer = CampaignAnalyzer(campaigns)

    # 1. 投放总览
    overview = analyzer.get_overview()
    reporter.print_section("投放计划总览", overview)

    # 2. 关键词分析
    kw_analysis = analyzer.analyze_keywords()
    reporter.print_section("关键词分析", {
        "关键词总数": kw_analysis["关键词总数"],
        "优化建议": kw_analysis["优化建议"],
    })
    if kw_analysis.get("高ROI关键词TOP20"):
        reporter.print_section("高ROI关键词", kw_analysis["高ROI关键词TOP20"][:10])
    if kw_analysis.get("低效关键词(需优化)"):
        reporter.print_section("低效关键词(需优化)", kw_analysis["低效关键词(需优化)"][:10])

    # 3. 预算优化
    budget = analyzer.get_budget_optimization()
    reporter.print_section("预算分配优化", budget)

    # 4. 时段策略
    time_strategy = analyzer.get_time_strategy()
    reporter.print_section("投放时段策略", time_strategy)

    return {
        "投放总览": overview,
        "关键词分析摘要": {"关键词总数": kw_analysis["关键词总数"], "优化建议": kw_analysis["优化建议"]},
        "预算优化": budget,
        "时段策略": time_strategy,
    }


def run_roi_optimization(campaigns, products, reporter) -> dict:
    """运行ROI优化"""
    console.print("\n[bold]━━━ 模块四：ROI优化 ━━━[/bold]", style="magenta")

    optimizer = ROIOptimizer(campaigns, products)

    # 1. ROI总览
    dashboard = optimizer.get_roi_dashboard()
    reporter.print_section("ROI多维度总览", {
        "整体ROI": dashboard["整体ROI"],
        "目标ROI": dashboard["目标ROI"],
        "按平台": dashboard["按平台"],
    })
    reporter.print_roi_health(dashboard["健康诊断"])

    # 2. 出价建议
    bid_suggestions = optimizer.get_bid_suggestions()
    if bid_suggestions:
        reporter.print_section("智能出价建议TOP15", bid_suggestions[:15])

    # 3. ROI预测
    prediction = optimizer.get_roi_prediction()
    reporter.print_section("ROI预测 - 场景分析", prediction["场景分析"])

    # 4. 行动计划
    action_plan = optimizer.get_optimization_action_plan()
    reporter.print_section("优化行动计划", action_plan)

    return {
        "ROI总览": {
            "整体ROI": dashboard["整体ROI"],
            "目标ROI": dashboard["目标ROI"],
            "按平台": dashboard["按平台"],
            "健康诊断": dashboard["健康诊断"],
        },
        "出价建议": bid_suggestions[:10] if bid_suggestions else [],
        "场景分析": prediction["场景分析"],
        "行动计划": action_plan,
    }


def main():
    parser = argparse.ArgumentParser(description="淘宝营销分析系统")
    parser.add_argument("--module", choices=["crowd", "cart", "campaign", "roi"],
                        help="仅运行指定模块")
    parser.add_argument("--export", action="store_true", help="导出HTML报告")
    parser.add_argument("--profiles", type=int, default=2000, help="模拟人群数量")
    args = parser.parse_args()

    print_banner()
    console.print("[dim]正在生成模拟数据...[/dim]")

    data = generate_all_sample_data()
    profiles = data["profiles"]
    products = data["products"]
    campaigns = data["campaigns"]

    reporter = Reporter(DEFAULT_CONFIG.report_output_dir)
    report_data = {}

    console.print(f"[green]数据就绪: {len(profiles)}个用户 | {len(products)}个商品 | {len(campaigns)}个投放计划[/green]\n")

    modules = {
        "crowd": ("人群分析", lambda: run_crowd_analysis(profiles, reporter)),
        "cart": ("收藏加购", lambda: run_cart_fav_analysis(products, profiles, reporter)),
        "campaign": ("投放分析", lambda: run_campaign_analysis(campaigns, reporter)),
        "roi": ("ROI优化", lambda: run_roi_optimization(campaigns, products, reporter)),
    }

    if args.module:
        name, func = modules[args.module]
        report_data[name] = func()
    else:
        for key, (name, func) in modules.items():
            report_data[name] = func()

    # 导出报告
    if args.export:
        reporter.export_html_report(report_data)

    console.print("\n[bold green]分析完成！[/bold green]")
    if not args.export:
        console.print("[dim]提示: 使用 --export 参数可导出HTML报告[/dim]")


if __name__ == "__main__":
    main()
