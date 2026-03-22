import { useState } from 'react'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'

const DEMO_TASKS = [
  { id: 1, task_no: 'RC-2024-03-001', platform: '天猫', period: '2024-03', status: 'completed', total_orders: 856, matched_orders: 842, discrepancy_orders: 14, match_rate: '98.4%', total_diff_amount: -1256.80, created_at: '2024-03-21' },
  { id: 2, task_no: 'RC-2024-03-002', platform: '京东自营', period: '2024-03', status: 'completed', total_orders: 432, matched_orders: 430, discrepancy_orders: 2, match_rate: '99.5%', total_diff_amount: -89.00, created_at: '2024-03-21' },
  { id: 3, task_no: 'RC-2024-02-001', platform: '天猫', period: '2024-02', status: 'completed', total_orders: 1023, matched_orders: 1018, discrepancy_orders: 5, match_rate: '99.5%', total_diff_amount: -432.50, created_at: '2024-03-05' },
]

const DEMO_RECORDS = [
  { id: 1, order_no: 'TB2024032100001', status: 'matched', system_amount: 1299.00, platform_amount: 1299.00, amount_diff: 0, reason: '' },
  { id: 2, order_no: 'TB2024032100015', status: 'discrepancy', system_amount: 459.00, platform_amount: 448.50, amount_diff: 10.50, reason: '佣金计算差异' },
  { id: 3, order_no: 'TB2024032100028', status: 'discrepancy', system_amount: 2688.00, platform_amount: 2688.00, amount_diff: 0, reason: '结算时间差异（跨月）' },
  { id: 4, order_no: 'TB2024032100032', status: 'matched', system_amount: 189.00, platform_amount: 189.00, amount_diff: 0, reason: '' },
  { id: 5, order_no: 'TB2024032100041', status: 'discrepancy', system_amount: 3560.00, platform_amount: 3524.00, amount_diff: 36.00, reason: '运费补差未同步' },
]

function fmt(v: number) { return `¥${v.toFixed(2)}` }

const recordColumns = [
  { key: 'order_no', title: '订单号' },
  { key: 'status', title: '状态', render: (r: any) => <StatusBadge status={r.status} /> },
  { key: 'system_amount', title: '系统金额', align: 'right' as const, render: (r: any) => fmt(r.system_amount) },
  { key: 'platform_amount', title: '平台金额', align: 'right' as const, render: (r: any) => fmt(r.platform_amount) },
  { key: 'amount_diff', title: '差异', align: 'right' as const, render: (r: any) => r.amount_diff !== 0 ? <span className="text-vermillion">{fmt(r.amount_diff)}</span> : <span className="text-ink-muted">-</span> },
  { key: 'reason', title: '差异原因', render: (r: any) => r.reason || <span className="text-ink-muted">-</span> },
]

export default function Reconciliation() {
  const [selectedTask, setSelectedTask] = useState<number | null>(null)

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-serif text-lg font-semibold text-ink">照合管理</h2>
          <p className="text-sm text-ink-muted mt-1">平台对账与差异分析</p>
        </div>
        <button className="px-4 py-1.5 bg-indigo text-white rounded-lg text-sm hover:bg-indigo-light transition-colors">
          新建对账
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-border-light p-4">
          <p className="text-xs text-ink-muted mb-1">平均匹配率</p>
          <p className="text-xl font-light text-moss">99.1%</p>
        </div>
        <div className="bg-white rounded-lg border border-border-light p-4">
          <p className="text-xs text-ink-muted mb-1">累计差异金额</p>
          <p className="text-xl font-light text-vermillion">¥-1,778.30</p>
        </div>
        <div className="bg-white rounded-lg border border-border-light p-4">
          <p className="text-xs text-ink-muted mb-1">未解决差异</p>
          <p className="text-xl font-light">21 笔</p>
        </div>
      </div>

      {/* Tasks List */}
      <div className="bg-white rounded-lg border border-border-light mb-6">
        <div className="px-4 py-3 border-b border-border-light">
          <h3 className="text-sm text-ink-light">对账任务</h3>
        </div>
        <div className="cursor-pointer">
          {DEMO_TASKS.map(task => (
            <div
              key={task.id}
              onClick={() => setSelectedTask(selectedTask === task.id ? null : task.id)}
              className={`grid grid-cols-8 gap-2 px-4 py-3 border-b border-border-light text-sm hover:bg-paper-warm/50 transition-colors ${
                selectedTask === task.id ? 'bg-paper-warm' : ''
              }`}
            >
              <span className="text-ink-light">{task.task_no}</span>
              <span>{task.platform}</span>
              <span className="text-ink-muted">{task.period}</span>
              <span><StatusBadge status={task.status} /></span>
              <span className="text-right text-moss">{task.match_rate}</span>
              <span className="text-right">{task.discrepancy_orders}</span>
              <span className={`text-right ${task.total_diff_amount < 0 ? 'text-vermillion' : ''}`}>{fmt(task.total_diff_amount)}</span>
              <span className="text-right text-ink-muted">{task.created_at}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Detail Records */}
      {selectedTask && (
        <div className="bg-white rounded-lg border border-border-light">
          <div className="px-4 py-3 border-b border-border-light flex items-center justify-between">
            <h3 className="text-sm text-ink-light">对账明细</h3>
            <span className="text-xs text-ink-muted">任务 {DEMO_TASKS.find(t => t.id === selectedTask)?.task_no}</span>
          </div>
          <DataTable columns={recordColumns} data={DEMO_RECORDS} />
        </div>
      )}
    </div>
  )
}
