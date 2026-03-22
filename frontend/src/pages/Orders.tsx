import { useState } from 'react'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import { api } from '../services/api'

const DEMO_ORDERS = [
  { id: 1, order_no: 'TB2024032100001', platform: 'tmall', status: 'completed', total_amount: 1299.00, commission_amount: 64.95, settlement_amount: 1234.05, buyer_name: '张**', order_time: '2024-03-21 14:32:00' },
  { id: 2, order_no: 'TB2024032100002', platform: 'tmall', status: 'paid', total_amount: 459.00, commission_amount: 22.95, settlement_amount: 436.05, buyer_name: '李**', order_time: '2024-03-21 15:18:00' },
  { id: 3, order_no: 'JD2024032100001', platform: 'jd_self', status: 'shipped', total_amount: 2688.00, commission_amount: 215.04, settlement_amount: 2472.96, buyer_name: '王**', order_time: '2024-03-21 09:45:00' },
  { id: 4, order_no: 'TB2024032100003', platform: 'taobao', status: 'refunded', total_amount: 189.00, commission_amount: 9.45, settlement_amount: 0, buyer_name: '陈**', order_time: '2024-03-20 20:11:00', refund_amount: 189.00 },
  { id: 5, order_no: 'JD2024032100002', platform: 'jd_pop', status: 'completed', total_amount: 3560.00, commission_amount: 284.80, settlement_amount: 3275.20, buyer_name: '赵**', order_time: '2024-03-20 11:27:00' },
  { id: 6, order_no: 'TB2024032100004', platform: 'tmall', status: 'pending', total_amount: 799.00, commission_amount: 0, settlement_amount: 0, buyer_name: '刘**', order_time: '2024-03-21 16:55:00' },
]

const platformLabels: Record<string, string> = {
  tmall: '天猫',
  taobao: '淘宝',
  jd_self: '京东自营',
  jd_pop: '京东POP',
}

function fmt(val: number) {
  return `¥${val.toFixed(2)}`
}

const columns = [
  { key: 'order_no', title: '订单号' },
  {
    key: 'platform',
    title: '平台',
    render: (r: any) => <span className="text-ink-light">{platformLabels[r.platform] || r.platform}</span>,
  },
  {
    key: 'status',
    title: '状态',
    render: (r: any) => <StatusBadge status={r.status} />,
  },
  { key: 'total_amount', title: '订单金额', align: 'right' as const, render: (r: any) => fmt(r.total_amount) },
  { key: 'commission_amount', title: '佣金', align: 'right' as const, render: (r: any) => fmt(r.commission_amount) },
  { key: 'settlement_amount', title: '结算金额', align: 'right' as const, render: (r: any) => fmt(r.settlement_amount) },
  { key: 'buyer_name', title: '买家' },
  {
    key: 'order_time',
    title: '下单时间',
    render: (r: any) => <span className="text-ink-muted tabular-nums">{r.order_time?.slice(0, 16)}</span>,
  },
]

export default function Orders() {
  const [orders, setOrders] = useState(DEMO_ORDERS)
  const [importing, setImporting] = useState(false)
  const [platform, setPlatform] = useState('tmall')
  const [filter, setFilter] = useState('')

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const result = await api.importOrders(file, platform)
      if (result.orders) setOrders(prev => [...result.orders, ...prev])
    } catch {
      // demo mode
    }
    setImporting(false)
    e.target.value = ''
  }

  const filtered = filter
    ? orders.filter(o => o.platform === filter)
    : orders

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-serif text-lg font-semibold text-ink">注文管理</h2>
          <p className="text-sm text-ink-muted mt-1">订单查看与导入</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="text-sm border border-border rounded-lg px-3 py-1.5 bg-white text-ink-light focus:outline-none focus:border-indigo"
          >
            <option value="tmall">天猫</option>
            <option value="taobao">淘宝</option>
            <option value="jd_self">京东自营</option>
            <option value="jd_pop">京东POP</option>
          </select>
          <label className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo text-white rounded-lg text-sm cursor-pointer hover:bg-indigo-light transition-colors">
            {importing ? '导入中...' : '导入订单'}
            <input type="file" className="hidden" accept=".csv,.xlsx,.xls" onChange={handleImport} disabled={importing} />
          </label>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 border-b border-border-light">
        {[{ key: '', label: '全部' }, ...Object.entries(platformLabels).map(([k, v]) => ({ key: k, label: v }))].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-2 text-sm transition-colors relative ${
              filter === f.key
                ? 'text-ink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-ink'
                : 'text-ink-muted hover:text-ink-light'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-border-light">
        <DataTable columns={columns} data={filtered} emptyText="暂无订单数据" />
      </div>
    </div>
  )
}
