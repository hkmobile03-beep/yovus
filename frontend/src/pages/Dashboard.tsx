import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import MetricCard from '../components/MetricCard'
import { api } from '../services/api'

const DEMO_METRICS = {
  total_revenue: 2856432.50,
  total_orders: 12847,
  avg_order_value: 222.26,
  refund_rate: 3.2,
  gross_margin: 34.5,
  tax_payable: 128450.00,
  pending_reconciliation: 3,
  alert_count: 2,
}

const DEMO_TREND = [
  { month: '10月', revenue: 198000, cost: 129000 },
  { month: '11月', revenue: 245000, cost: 158000 },
  { month: '12月', revenue: 312000, cost: 198000 },
  { month: '1月', revenue: 278000, cost: 176000 },
  { month: '2月', revenue: 189000, cost: 125000 },
  { month: '3月', revenue: 356000, cost: 218000 },
]

const DEMO_PLATFORM = [
  { name: '天猫', value: 45 },
  { name: '京东自营', value: 30 },
  { name: '淘宝', value: 15 },
  { name: '京东POP', value: 10 },
]

const PIE_COLORS = ['#3d5a80', '#5a7247', '#b8860b', '#7b6b8a']

function formatCurrency(val: number) {
  return `¥${val.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState(DEMO_METRICS)
  const [trend, setTrend] = useState(DEMO_TREND)
  const [platform, setPlatform] = useState(DEMO_PLATFORM)

  useEffect(() => {
    api.getDashboard().then(data => {
      if (data) {
        setMetrics(prev => ({ ...prev, ...data }))
        if (data.revenue_trend) setTrend(data.revenue_trend)
        if (data.platform_distribution) setPlatform(data.platform_distribution)
      }
    }).catch(() => {})
  }, [])

  return (
    <div>
      <div className="mb-8">
        <h2 className="font-serif text-lg font-semibold text-ink">経営概要</h2>
        <p className="text-sm text-ink-muted mt-1">业务全局一览</p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          title="总营收"
          value={formatCurrency(metrics.total_revenue)}
          trend="up"
          trendValue="12.3%"
          accent="indigo"
        />
        <MetricCard
          title="订单量"
          value={metrics.total_orders.toLocaleString()}
          trend="up"
          trendValue="8.7%"
          accent="moss"
        />
        <MetricCard
          title="毛利率"
          value={`${metrics.gross_margin}%`}
          trend="neutral"
          trendValue="持平"
          accent="gold"
        />
        <MetricCard
          title="退款率"
          value={`${metrics.refund_rate}%`}
          trend="down"
          trendValue="0.5%"
          accent="vermillion"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Revenue Trend */}
        <div className="col-span-2 bg-white rounded-lg border border-border-light p-6">
          <h3 className="text-sm text-ink-muted mb-4 tracking-wider">营收趋势</h3>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trend}>
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3d5a80" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#3d5a80" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#c1554d" stopOpacity={0.1} />
                  <stop offset="100%" stopColor="#c1554d" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#edecea" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} tickLine={false}
                tickFormatter={v => `${(v/10000).toFixed(0)}万`} />
              <Tooltip
                contentStyle={{ border: '1px solid #e0dfdb', borderRadius: '8px', fontSize: '13px', boxShadow: 'none' }}
                formatter={(val: any) => formatCurrency(Number(val))}
              />
              <Area type="monotone" dataKey="revenue" name="营收" stroke="#3d5a80" fill="url(#revenueGrad)" strokeWidth={1.5} />
              <Area type="monotone" dataKey="cost" name="成本" stroke="#c1554d" fill="url(#costGrad)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Platform Distribution */}
        <div className="bg-white rounded-lg border border-border-light p-6">
          <h3 className="text-sm text-ink-muted mb-4 tracking-wider">平台分布</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={platform}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={75}
                dataKey="value"
                stroke="none"
              >
                {platform.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ border: '1px solid #e0dfdb', borderRadius: '8px', fontSize: '13px', boxShadow: 'none' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-3 justify-center mt-2">
            {platform.map((p, i) => (
              <div key={p.name} className="flex items-center gap-1.5 text-xs text-ink-muted">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i] }} />
                {p.name} {p.value}%
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Status */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-border-light p-5">
          <p className="text-xs text-ink-muted tracking-wider mb-2">应缴增值税</p>
          <p className="text-lg font-light">{formatCurrency(metrics.tax_payable)}</p>
        </div>
        <div className="bg-white rounded-lg border border-border-light p-5">
          <p className="text-xs text-ink-muted tracking-wider mb-2">待对账任务</p>
          <p className="text-lg font-light">{metrics.pending_reconciliation} <span className="text-xs text-ink-muted">项</span></p>
        </div>
        <div className="bg-white rounded-lg border border-border-light p-5">
          <p className="text-xs text-ink-muted tracking-wider mb-2">活跃告警</p>
          <p className="text-lg font-light">{metrics.alert_count} <span className="text-xs text-ink-muted">条</span></p>
        </div>
      </div>
    </div>
  )
}
