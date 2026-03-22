"""AI 分析服务 - 基于大语言模型的财务数据智能分析"""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus, Platform
from app.models.finance import AccountingVoucher
from app.models.reconciliation import ReconciliationTask
from app.models.tax import VATInvoice


class AIAnalysisService:
    """聚合财务数据，构建分析上下文，调用 LLM 生成洞察"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(self, question: str, context_type: str = "general", period: str | None = None) -> dict:
        """主分析入口"""
        context = await self._build_context(context_type, period)
        analysis = await self._generate_analysis(question, context)
        return analysis

    async def _build_context(self, context_type: str, period: str | None = None) -> str:
        """从数据库聚合关键指标构建分析上下文"""
        parts = []

        if context_type in ("general", "orders", "profit"):
            order_stats = await self._get_order_stats(period)
            parts.append(f"【订单概况】\n{order_stats}")

        if context_type in ("general", "reconciliation"):
            recon_stats = await self._get_reconciliation_stats(period)
            parts.append(f"【对账概况】\n{recon_stats}")

        if context_type in ("general", "tax"):
            tax_stats = await self._get_tax_stats(period)
            parts.append(f"【税务概况】\n{tax_stats}")

        if context_type in ("general", "profit"):
            profit_stats = await self._get_profit_stats(period)
            parts.append(f"【损益概况】\n{profit_stats}")

        return "\n\n".join(parts) if parts else "暂无可用数据上下文"

    async def _get_order_stats(self, period: str | None) -> str:
        query = select(
            func.count(Order.id).label("total"),
            func.sum(Order.total_amount).label("revenue"),
            func.sum(Order.refund_amount).label("refunds"),
            func.sum(Order.commission_amount).label("commission"),
            func.avg(Order.total_amount).label("avg_order"),
        )
        if period:
            query = query.where(func.to_char(Order.order_time, "YYYY-MM") == period)

        result = await self.db.execute(query)
        row = result.one_or_none()
        if not row or not row.total:
            return "暂无订单数据"

        # 按平台统计
        platform_query = select(
            Order.platform,
            func.count(Order.id).label("count"),
            func.sum(Order.total_amount).label("amount"),
        ).group_by(Order.platform)
        if period:
            platform_query = platform_query.where(func.to_char(Order.order_time, "YYYY-MM") == period)
        platform_result = await self.db.execute(platform_query)
        platforms = platform_result.all()

        lines = [
            f"总订单数: {row.total}",
            f"总营收: ¥{row.revenue or 0:,.2f}",
            f"退款金额: ¥{row.refunds or 0:,.2f}",
            f"平台佣金: ¥{row.commission or 0:,.2f}",
            f"平均客单价: ¥{row.avg_order or 0:,.2f}",
        ]
        for p in platforms:
            lines.append(f"  {p.platform}: {p.count}单, ¥{p.amount or 0:,.2f}")

        return "\n".join(lines)

    async def _get_reconciliation_stats(self, period: str | None) -> str:
        query = select(ReconciliationTask)
        if period:
            query = query.where(ReconciliationTask.period == period)
        query = query.order_by(ReconciliationTask.created_at.desc()).limit(5)
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return "暂无对账数据"

        lines = []
        for t in tasks:
            lines.append(
                f"{t.period} {t.platform}: 匹配率 {t.match_rate}, "
                f"差异 {t.discrepancy_orders}笔 ¥{t.total_diff_amount or 0:,.2f}"
            )
        return "\n".join(lines)

    async def _get_tax_stats(self, period: str | None) -> str:
        from app.models.tax import InvoiceDirection

        target_period = period or datetime.now().strftime("%Y-%m")

        # 销项发票
        out_query = select(
            func.count(VATInvoice.id).label("count"),
            func.sum(VATInvoice.amount).label("amount"),
            func.sum(VATInvoice.tax_amount).label("tax"),
        ).where(
            VATInvoice.direction == InvoiceDirection.OUTPUT,
            VATInvoice.period == target_period,
        )
        out_result = await self.db.execute(out_query)
        out = out_result.one()

        # 进项发票
        in_query = select(
            func.count(VATInvoice.id).label("count"),
            func.sum(VATInvoice.amount).label("amount"),
            func.sum(VATInvoice.tax_amount).label("tax"),
        ).where(
            VATInvoice.direction == InvoiceDirection.INPUT,
            VATInvoice.period == target_period,
            VATInvoice.is_certified == True,
        )
        in_result = await self.db.execute(in_query)
        inp = in_result.one()

        output_tax = out.tax or Decimal("0")
        input_tax = inp.tax or Decimal("0")
        payable = output_tax - input_tax

        return "\n".join([
            f"期间: {target_period}",
            f"销项发票: {out.count or 0}张, 税额 ¥{output_tax:,.2f}",
            f"进项发票(已认证): {inp.count or 0}张, 税额 ¥{input_tax:,.2f}",
            f"应纳增值税: ¥{payable:,.2f}",
        ])

    async def _get_profit_stats(self, period: str | None) -> str:
        query = select(
            func.sum(Order.total_amount).label("revenue"),
            func.sum(Order.commission_amount).label("commission"),
            func.sum(Order.refund_amount).label("refunds"),
        ).where(Order.status == OrderStatus.COMPLETED)

        if period:
            query = query.where(func.to_char(Order.complete_time, "YYYY-MM") == period)

        result = await self.db.execute(query)
        row = result.one()

        revenue = row.revenue or Decimal("0")
        commission = row.commission or Decimal("0")
        refunds = row.refunds or Decimal("0")
        net_revenue = revenue - commission - refunds

        return "\n".join([
            f"已完成订单营收: ¥{revenue:,.2f}",
            f"平台佣金支出: ¥{commission:,.2f}",
            f"退款支出: ¥{refunds:,.2f}",
            f"净营收: ¥{net_revenue:,.2f}",
        ])

    async def _generate_analysis(self, question: str, context: str) -> dict:
        """调用 LLM 或使用规则引擎生成分析"""
        # 构建系统提示词
        system_prompt = (
            "你是一位资深的电商财务分析师，精通中国电商平台（天猫、淘宝、京东）的财务核算、"
            "税务申报、对账管理。请基于以下业务数据，用专业且易懂的语言回答问题。\n"
            "回答格式要求：使用 Markdown，包含数据表格、关键发现、建议。"
        )

        full_prompt = f"{system_prompt}\n\n{context}\n\n用户问题：{question}"

        # 尝试调用 Anthropic API
        try:
            import anthropic
            client = anthropic.Anthropic()
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{"role": "user", "content": full_prompt}],
            )
            analysis_text = message.content[0].text
        except Exception:
            # 降级为基于规则的分析
            analysis_text = self._rule_based_analysis(question, context)

        return {
            "analysis": analysis_text,
            "suggestions": [],
            "data_points": [],
        }

    def _rule_based_analysis(self, question: str, context: str) -> str:
        """当 LLM 不可用时的规则引擎降级方案"""
        return (
            f"## 数据概览\n\n"
            f"以下是基于当前数据库的分析：\n\n"
            f"```\n{context}\n```\n\n"
            f"### 您的问题\n{question}\n\n"
            f"> 提示：配置 ANTHROPIC_API_KEY 环境变量后，将启用 AI 深度分析能力。\n\n"
            f"### 基础分析\n"
            f"基于上述数据，系统已提取关键指标供您参考。"
            f"建议结合实际业务情况进行判断。"
        )
