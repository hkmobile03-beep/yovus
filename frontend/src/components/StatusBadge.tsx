const statusStyles: Record<string, string> = {
  completed: 'bg-moss/10 text-moss',
  matched: 'bg-moss/10 text-moss',
  paid: 'bg-indigo/10 text-indigo',
  pending: 'bg-gold/10 text-gold',
  discrepancy: 'bg-vermillion/10 text-vermillion',
  refunded: 'bg-vermillion/10 text-vermillion',
  cancelled: 'bg-ink-muted/10 text-ink-muted',
  warning: 'bg-gold/10 text-gold',
  critical: 'bg-vermillion/10 text-vermillion',
  info: 'bg-indigo/10 text-indigo',
  active: 'bg-moss/10 text-moss',
  resolved: 'bg-ink-muted/10 text-ink-muted',
}

const statusLabels: Record<string, string> = {
  completed: '已完成',
  matched: '已匹配',
  paid: '已支付',
  pending: '待处理',
  discrepancy: '有差异',
  refunded: '已退款',
  cancelled: '已取消',
  warning: '警告',
  critical: '严重',
  info: '提示',
  active: '活跃',
  resolved: '已解决',
  shipped: '已发货',
  delivered: '已收货',
}

interface StatusBadgeProps {
  status: string
  label?: string
}

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const s = status.toLowerCase()
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${statusStyles[s] || 'bg-paper-dark text-ink-muted'}`}>
      {label || statusLabels[s] || status}
    </span>
  )
}
