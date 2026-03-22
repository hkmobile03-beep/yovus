import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: '概览', icon: '◎' },
  { to: '/orders', label: '订单', icon: '帳' },
  { to: '/reconciliation', label: '对账', icon: '対' },
  { to: '/tax', label: '税务', icon: '税' },
  { to: '/profit', label: '损益', icon: '益' },
  { to: '/ai', label: 'AI 分析', icon: '智' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-paper-warm border-r border-border flex flex-col">
        <div className="px-6 py-8">
          <h1 className="font-serif text-xl font-semibold text-ink tracking-wider">
            悠数
          </h1>
          <p className="text-xs text-ink-muted mt-1 tracking-widest">
            电商财务管理
          </p>
        </div>

        <nav className="flex-1 px-3">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg mb-0.5 text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-paper text-ink font-normal shadow-sm'
                    : 'text-ink-muted hover:text-ink-light hover:bg-paper/50'
                }`
              }
            >
              <span className="text-base font-serif opacity-60">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-6 py-6 border-t border-border-light">
          <p className="text-xs text-ink-muted">v1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
