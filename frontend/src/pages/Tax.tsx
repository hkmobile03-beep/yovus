import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import MetricCard from '../components/MetricCard'

const DEMO_VAT = {
  period: '2024-03',
  output_tax: 48562.35,
  input_tax: 32180.00,
  tax_payable: 16382.35,
  carryforward: 0,
  surcharges: { urban_maintenance: 1146.76, education: 491.47, local_education: 327.65, total: 1965.88 },
}

const DEMO_INCOME = {
  year: '2024',
  revenue: 2856432.50,
  cost: 1870860.00,
  expense: 428465.00,
  taxable_income: 557107.50,
  tax_rate: 25,
  tax_amount: 139276.88,
}

const DEMO_VAT_TREND = [
  { month: '10月', output: 38200, input: 25600, payable: 12600 },
  { month: '11月', output: 42800, input: 29100, payable: 13700 },
  { month: '12月', output: 51200, input: 34800, payable: 16400 },
  { month: '1月', output: 45600, input: 31200, payable: 14400 },
  { month: '2月', output: 31000, input: 22500, payable: 8500 },
  { month: '3月', output: 48562, input: 32180, payable: 16382 },
]

const DEMO_INVOICE_STATUS = [
  { category: '平台佣金', has_special: 12, has_general: 2, no_invoice: 0, amount: 142680.50 },
  { category: '直通车推广', has_special: 6, has_general: 0, no_invoice: 1, amount: 86420.00 },
  { category: '物流费用', has_special: 8, has_general: 3, no_invoice: 2, amount: 45320.00 },
  { category: '仓储费', has_special: 4, has_general: 0, no_invoice: 0, amount: 18600.00 },
]

function fmt(v: number) { return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` }

export default function Tax() {
  const [activeTab, setActiveTab] = useState<'vat' | 'income' | 'invoice'>('vat')

  return (
    <div>
      <div className="mb-8">
        <h2 className="font-serif text-lg font-semibold text-ink">税務管理</h2>
        <p className="text-sm text-ink-muted mt-1">增值税、所得税计算与发票管理</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border-light">
        {[
          { key: 'vat', label: '增值税' },
          { key: 'income', label: '企业所得税' },
          { key: 'invoice', label: '发票管理' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 text-sm transition-colors relative ${
              activeTab === tab.key
                ? 'text-ink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-ink'
                : 'text-ink-muted hover:text-ink-light'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'vat' && (
        <div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard title="销项税额" value={fmt(DEMO_VAT.output_tax)} accent="indigo" />
            <MetricCard title="进项税额" value={fmt(DEMO_VAT.input_tax)} accent="moss" />
            <MetricCard title="应纳税额" value={fmt(DEMO_VAT.tax_payable)} accent="vermillion" />
            <MetricCard title="附加税合计" value={fmt(DEMO_VAT.surcharges.total)} accent="gold" />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white rounded-lg border border-border-light p-6">
              <h3 className="text-sm text-ink-muted mb-4 tracking-wider">增值税趋势</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={DEMO_VAT_TREND}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#edecea" />
                  <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#8a8a8a' }} axisLine={false} tickFormatter={v => `${(v/10000).toFixed(0)}万`} />
                  <Tooltip contentStyle={{ border: '1px solid #e0dfdb', borderRadius: '8px', fontSize: '13px', boxShadow: 'none' }} />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="output" name="销项" fill="#3d5a80" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="input" name="进项" fill="#5a7247" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="payable" name="应纳" fill="#c1554d" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-lg border border-border-light p-6">
              <h3 className="text-sm text-ink-muted mb-4 tracking-wider">附加税明细</h3>
              <div className="space-y-4 mt-6">
                {[
                  { label: '城市维护建设税 (7%)', value: DEMO_VAT.surcharges.urban_maintenance },
                  { label: '教育费附加 (3%)', value: DEMO_VAT.surcharges.education },
                  { label: '地方教育附加 (2%)', value: DEMO_VAT.surcharges.local_education },
                ].map(item => (
                  <div key={item.label} className="flex items-center justify-between py-3 border-b border-border-light last:border-0">
                    <span className="text-sm text-ink-light">{item.label}</span>
                    <span className="text-sm tabular-nums">{fmt(item.value)}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between pt-2">
                  <span className="text-sm font-normal text-ink">合计</span>
                  <span className="text-sm font-normal tabular-nums">{fmt(DEMO_VAT.surcharges.total)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'income' && (
        <div className="bg-white rounded-lg border border-border-light p-6">
          <h3 className="text-sm text-ink-muted mb-6 tracking-wider">企业所得税计算（{DEMO_INCOME.year}年度）</h3>
          <div className="max-w-lg space-y-4">
            {[
              { label: '营业收入', value: DEMO_INCOME.revenue },
              { label: '营业成本', value: -DEMO_INCOME.cost },
              { label: '期间费用', value: -DEMO_INCOME.expense },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between py-2 border-b border-border-light">
                <span className="text-sm text-ink-light">{item.label}</span>
                <span className={`text-sm tabular-nums ${item.value < 0 ? 'text-vermillion' : ''}`}>
                  {item.value < 0 ? '-' : ''}{fmt(Math.abs(item.value))}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-sm font-normal">应纳税所得额</span>
              <span className="text-sm font-normal tabular-nums">{fmt(DEMO_INCOME.taxable_income)}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border-light">
              <span className="text-sm text-ink-light">税率</span>
              <span className="text-sm tabular-nums">{DEMO_INCOME.tax_rate}%</span>
            </div>
            <div className="flex items-center justify-between py-3 bg-paper-warm -mx-2 px-2 rounded">
              <span className="text-sm font-normal text-ink">应纳所得税额</span>
              <span className="text-base font-normal tabular-nums text-vermillion">{fmt(DEMO_INCOME.tax_amount)}</span>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'invoice' && (
        <div className="bg-white rounded-lg border border-border-light">
          <div className="px-4 py-3 border-b border-border-light">
            <h3 className="text-sm text-ink-light">平台费用发票状态</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-xs text-ink-muted">
                <th className="px-4 py-3 text-left font-normal">费用类别</th>
                <th className="px-4 py-3 text-right font-normal">金额</th>
                <th className="px-4 py-3 text-center font-normal">专票</th>
                <th className="px-4 py-3 text-center font-normal">普票</th>
                <th className="px-4 py-3 text-center font-normal">未取得</th>
                <th className="px-4 py-3 text-center font-normal">进项可抵扣</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_INVOICE_STATUS.map(row => (
                <tr key={row.category} className="border-b border-border-light text-sm">
                  <td className="px-4 py-3">{row.category}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{fmt(row.amount)}</td>
                  <td className="px-4 py-3 text-center"><span className="text-moss">{row.has_special}</span></td>
                  <td className="px-4 py-3 text-center">{row.has_general}</td>
                  <td className="px-4 py-3 text-center">{row.no_invoice > 0 ? <span className="text-vermillion">{row.no_invoice}</span> : '-'}</td>
                  <td className="px-4 py-3 text-center">{row.has_special > 0 ? <span className="text-moss">是</span> : <span className="text-ink-muted">否</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
