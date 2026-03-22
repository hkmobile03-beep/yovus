"""数据可视化与报表生成

支持:
- 终端Rich表格展示
- HTML报告导出
"""

import json
import os
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box


console = Console()


class Reporter:
    """报表生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── 终端展示 ──────────────────────────────────────────

    def print_section(self, title: str, data: Any):
        """通用数据展示"""
        console.print()
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))

        if isinstance(data, dict):
            self._print_dict(data)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            self._print_table_from_dicts(data, title)
        elif isinstance(data, list):
            for item in data:
                console.print(f"  - {item}")
        else:
            console.print(f"  {data}")

    def _print_dict(self, data: dict, indent: int = 0):
        """递归打印字典"""
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                console.print(f"{prefix}[bold]{key}:[/bold]")
                self._print_dict(value, indent + 1)
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    console.print(f"{prefix}[bold]{key}:[/bold]")
                    self._print_table_from_dicts(value, key)
                elif value and isinstance(value[0], str):
                    console.print(f"{prefix}[bold]{key}:[/bold]")
                    for item in value:
                        console.print(f"{prefix}  - {item}")
                else:
                    console.print(f"{prefix}[bold]{key}:[/bold] {value}")
            else:
                console.print(f"{prefix}[bold]{key}:[/bold] {value}")

    def _print_table_from_dicts(self, data: list[dict], title: str = ""):
        """从字典列表生成Rich表格"""
        if not data:
            return

        table = Table(title=title, box=box.ROUNDED, show_lines=True)
        keys = list(data[0].keys())

        for key in keys:
            table.add_column(str(key), style="cyan", no_wrap=False)

        for row in data:
            table.add_row(*[str(row.get(k, "")) for k in keys])

        console.print(table)

    def print_roi_health(self, health_data: dict):
        """ROI健康度展示"""
        level = health_data.get("健康等级", "未知")
        color_map = {"green": "green", "blue": "blue", "yellow": "yellow", "red": "red"}
        color = color_map.get(health_data.get("状态", ""), "white")

        panel_content = (
            f"[bold {color}]ROI健康等级: {level}[/bold {color}]\n"
            f"优秀计划: {health_data.get('优秀计划数', 0)}个  "
            f"待优化: {health_data.get('待优化计划数', 0)}个"
        )
        console.print(Panel(panel_content, title="ROI健康诊断", border_style=color))

        suggestions = health_data.get("建议", [])
        if suggestions:
            for s in suggestions:
                console.print(f"  [yellow]>[/yellow] {s}")

    def print_funnel(self, funnel: dict):
        """转化漏斗可视化"""
        steps = ["展现量", "点击量", "收藏加购合计", "成交笔数"]
        values = [funnel.get(s, 0) for s in steps]
        max_val = max(values) if values else 1

        console.print(Panel("[bold]转化漏斗[/bold]", expand=False))
        for step, val in zip(steps, values):
            bar_len = int(val / max_val * 40) if max_val > 0 else 0
            bar = "█" * bar_len
            console.print(f"  {step:12s} | [green]{bar}[/green] {val:,}")

        # 各环节转化率
        rates = ["点击率", "收藏加购率", "收藏加购→成交转化率"]
        for r in rates:
            if r in funnel:
                console.print(f"  {r}: [bold]{funnel[r]}[/bold]")

        # 瓶颈诊断
        if "瓶颈诊断" in funnel:
            console.print("\n  [bold red]瓶颈诊断:[/bold red]")
            for d in funnel["瓶颈诊断"]:
                console.print(f"    [yellow]![/yellow] {d}")

    # ── HTML报告导出 ──────────────────────────────────────

    def export_html_report(self, report_data: dict, filename: str = None) -> str:
        """导出HTML报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"taobao_report_{timestamp}.html"

        filepath = os.path.join(self.output_dir, filename)

        html = self._generate_html(report_data)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        console.print(f"\n[green]报告已导出: {filepath}[/green]")
        return filepath

    def _generate_html(self, report_data: dict) -> str:
        """生成HTML报告内容"""
        sections_html = ""
        for title, data in report_data.items():
            sections_html += f"<h2>{title}</h2>\n"
            sections_html += self._data_to_html(data)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>淘宝营销分析报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #ff4400; text-align: center; padding: 20px; background: white; border-radius: 8px; }}
        h2 {{ color: #333; border-left: 4px solid #ff4400; padding-left: 12px; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; background: white; border-radius: 8px; overflow: hidden; }}
        th {{ background: #ff4400; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #fff5f0; }}
        .metric {{ display: inline-block; background: white; padding: 15px 20px; margin: 5px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #ff4400; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .suggestion {{ background: #fff8e1; padding: 10px 15px; margin: 5px 0; border-left: 3px solid #ffa000; border-radius: 4px; }}
        .timestamp {{ text-align: center; color: #999; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>淘宝营销分析报告</h1>
    {sections_html}
    <p class="timestamp">报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</body>
</html>"""

    def _data_to_html(self, data: Any) -> str:
        """将数据转为HTML"""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return self._dicts_to_html_table(data)
        elif isinstance(data, dict):
            html = ""
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    html += f"<h3>{key}</h3>\n"
                    html += self._dicts_to_html_table(value)
                elif isinstance(value, list) and value and isinstance(value[0], str):
                    html += f"<h3>{key}</h3>\n"
                    for item in value:
                        html += f'<div class="suggestion">{item}</div>\n'
                elif isinstance(value, dict):
                    html += f"<h3>{key}</h3>\n"
                    html += self._data_to_html(value)
                else:
                    html += f'<div class="metric"><div class="metric-label">{key}</div><div class="metric-value">{value}</div></div>\n'
            return html
        else:
            return f"<p>{data}</p>"

    def _dicts_to_html_table(self, data: list[dict]) -> str:
        """字典列表转HTML表格"""
        if not data:
            return ""
        keys = list(data[0].keys())
        header = "".join(f"<th>{k}</th>" for k in keys)
        rows = ""
        for row in data:
            cells = "".join(f"<td>{row.get(k, '')}</td>" for k in keys)
            rows += f"<tr>{cells}</tr>\n"
        return f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>\n"
