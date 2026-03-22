import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, LineChart, Line } from 'recharts'
import MetricCard from '../components/MetricCard'
import DataTable from '../components/DataTable'

const DEMO_SUMMARY = {
  total_revenue: 356000,
  total_cost: 232400,
  gross_profit: 123600,
  gross_margin: 34.7,
  net_profit: 89200,
  net_margin: 25.1,
}

const DEMO_MARGIN_TREND = [
  { month: '10月', gross_margin: 34.8, net_margin: 24.2 },
  { month: '11月', gross_margin: 35.5, net_margin: 25.1 },
  { month: '12月', gross_margin: 36.5, net_margin: 26.8 },
  { month: '1月', gross_margin: 36.7, net_margin: 25.5 },
  { month: '2月', gross_margin: 33.9, net_margin: 23.1 },
  { month: '3月', gross_margin: 34.7, net_margin: 25.1 },
]

const DEMO_SKU = [
  { sku: 'SKU-001', product_name: '精华液 50ml', quantity: 1245, revenue: 124500, cost: 37350, profit: 87150, margin: 70.0 },
  { sku: 'SKU-002', product_name: '面膜套装 (10片)', quantity: 2380, revenue: 95200, cost: 47600, profit: 47600, margin: 50.0 },
  { sku: 'SKU-003', product_name: '洁面乳 120ml', quantity: 890, revenue: 44500, cost: 22250, profit: 22250, margin: 50.0 },
  { sku: 'SKU-004', product_name: '防晒霜 SPF50', quantity: 1560, revenue: 46800, cost: 28080, profit: 18720, margin: 40.0 },
  { sku: 'SKU-005', product_name: '眼霜 15ml', quantity: 420, revenue: 33600, cost: 16800, profit: 16800, margin: 50.0 },
]

const DEMO_PLATFORM_ROI = [
  { platform: '天猫', revenue: 160200, commission: 8010, promotion: 12000, logistics: 6400, total_cost: 26410, profit: 133790, roi: 506.6 },
  { platform: '京东自营', revenue: 106800, commission: 8544, promotion: 5000, logistics: 4272, total_cost: 17816, profit: 88984, roi: 499.5 },
  { platform: '淘宝', revenue: 53400, commission: 2670, promotion: 8000, logistics: 2136, total_cost: 12806, profit: 40594, roi: 317.0 },
  { platform: '京东POP', revenue: 35600, commission: 2848, promotion: 3000, logistics: 1424, total_cost: 7272, profit: 28328, roi: 389.5 },
]

function fmt(v: number) { return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` }
function fmtK(v: number) { return `¥${(v/1000).toFixed(1)}k` }

const skuColumns = [
  { key: 'sku', title: 'SKU' },
  { key: 'product_name', title: '商品名称' },
  { key: 'quantity', title: '销量', align: 'right' as const },
  { key: 'revenue', title: '营收', align: 'right' as const, render: (r: any) => fmtK(r.revenue) },
  { key: 'cost', title: '成本', align: 'right' as const, render: (r: any) => fmtK(r.cost) },
  { key: 'profit', title: '利润', align: 'right' as const, render: (r: any) => <span className="text-moss">{fmtK(r.profit)}</span> },
  {
    key: 'margin', title: '毛利率', align: 'right' as const,
    render: (r: any) => (
      <div className="flex items-center justify-end gap-2">
        <div className="w-16 h-1.5 bg-paper-dark rounded-full overflow-hidden">
          <div className="h-full bg-indigo rounded-full" style={{ width: `${r.margin}%` }} />
        </div>
        <span className="text-xs tabular-nums w-10 text-right">{r.margin}%</span>
      </div>
    ),
  },
]

export default function Profit() {
  const [tab, setTab] = useState<'overview' | 'sku' | 'platform'>('overview')

  return (
    <div>
      <div className="mb-8">
        <h2 className="font-serif text-lg font-semibold text-ink">損益分析</h2>
        <p className="text-sm text-ink-muted mt-1">利润分析与投资回报</p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-border-light">
        {[
          { key: 'overview', label: '总体概览' },
          { key: 'sku', label: 'SKU 分析' },
          { key: 'platform', label: '平台 ROI' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as any)}
            className={`px-4 py-2 text-sm transition-colors relative ${
              tab === t.key
                ? 'text-ink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-ink'
                : 'text-ink-muted hover:text-ink-light'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <MetricCard title="总营收" value={fmt(DEMO_SUMMARY.total_revenue)} accent="indigo" />
            <MetricCard title="毛利润" value={fmt(DEMO_SUMMARY.gross_profit)} subtitle={`毛利率 ${DEMO_SUMMARY.gross_margin}%`} accent="moss" />
            <MetricCard title="净利润" value={fmt(DEMO_SUMMARY.net_profit)} subtitle={`净利率 ${DEMO_SUMMARY.net_margin}%`} accent="gold" />
          </div>

          <div className="bg-white rounded-lg border border-border-light p-6">
            <h3 className="text-sm text-ink-muted mb-4 tracking-wider">利润率趋势</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={DEMO_MARGIN_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#edecea" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} domain={[20, 40]} unit="%" />
                <Tooltip contentStyle={{ border: '1px solid #e0dfdb', borderRadius: '8px', fontSize: '13px', boxShadow: 'none' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="gross_margin" name="毛利率" stroke="#3d5a80" strokeWidth={1.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="net_margin" name="净利率" stroke="#5a7247" strokeWidth={1.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === 'sku' && (
        <div className="bg-white rounded-lg border border-border-light">
          <div className="px-4 py-3 border-b border-border-light">
            <h3 className="text-sm text-ink-light">SKU 级别利润分析</h3>
          </div>
          <DataTable columns={skuColumns} data={DEMO_SKU} />
        </div>
      )}

      {tab === 'platform' && (
        <div>
          <div className="bg-white rounded-lg border border-border-light p-6 mb-6">
            <h3 className="text-sm text-ink-muted mb-4 tracking-wider">各平台投资回报率</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={DEMO_PLATFORM_ROI}>
                <CartesianGrid strokeDasharray="3 3" stroke="#edecea" />
                <XAxis dataKey="platform" tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} tickFormatter={v => `${v}%`} />
                <Tooltip contentStyle={{ border: '1px solid #e0dfdb', borderRadius: '8px', fontSize: '13px', boxShadow: 'none' }} />
                <Bar dataKey="roi" name="ROI" fill="#3d5a80" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-lg border border-border-light">
            <div className="px-4 py-3 border-b border-border-light">
              <h3 className="text-sm text-ink-light">平台费用结构</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-ink-muted">
                  <th className="px-4 py-3 text-left font-normal">平台</th>
                  <th className="px-4 py-3 text-right font-normal">营收</th>
                  <th className="px-4 py-3 text-right font-normal">佣金</th>
                  <th className="px-4 py-3 text-right font-normal">推广</th>
                  <th className="px-4 py-3 text-right font-normal">物流</th>
                  <th className="px-4 py-3 text-right font-normal">利润</th>
                  <th className="px-4 py-3 text-right font-normal">ROI</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_PLATFORM_ROI.map(row => (
                  <tr key={row.platform} className="border-b border-border-light hover:bg-paper-warm/50">
                    <td className="px-4 py-3">{row.platform}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{fmtK(row.revenue)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-ink-muted">{fmtK(row.commission)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-ink-muted">{fmtK(row.promotion)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-ink-muted">{fmtK(row.logistics)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-moss">{fmtK(row.profit)}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-normal">{row.roi}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
