interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  accent?: 'indigo' | 'vermillion' | 'moss' | 'gold' | 'wisteria'
}

const accentBorder: Record<string, string> = {
  indigo: 'border-l-indigo',
  vermillion: 'border-l-vermillion',
  moss: 'border-l-moss',
  gold: 'border-l-gold',
  wisteria: 'border-l-wisteria',
}

export default function MetricCard({ title, value, subtitle, trend, trendValue, accent = 'indigo' }: MetricCardProps) {
  return (
    <div className={`bg-white rounded-lg border border-border-light p-5 border-l-2 ${accentBorder[accent]}`}>
      <p className="text-xs text-ink-muted tracking-wider uppercase mb-3">{title}</p>
      <p className="text-2xl font-light text-ink tabular-nums">{value}</p>
      {(subtitle || trendValue) && (
        <div className="flex items-center gap-2 mt-2">
          {trendValue && (
            <span className={`text-xs ${
              trend === 'up' ? 'text-moss' : trend === 'down' ? 'text-vermillion' : 'text-ink-muted'
            }`}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '·'} {trendValue}
            </span>
          )}
          {subtitle && <span className="text-xs text-ink-muted">{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
