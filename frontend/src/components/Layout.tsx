import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Wallet,
  ScrollText,
  Bot,
  Layers,
  Settings,
  Shield,
  Zap,
  Activity,
} from 'lucide-react'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/wallet', icon: Wallet, label: 'Fuel Wallet' },
  { to: '/transactions', icon: ScrollText, label: 'Transactions' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/pillars', icon: Layers, label: 'Pillars' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-900/30 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-fortress-500 to-fortress-700 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display font-bold text-white">Dutchkem</h1>
              <p className="text-[10px] uppercase tracking-[0.2em] text-fortress-400">Fortress Suite</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.to
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'bg-fortress-600/20 text-fortress-400 border border-fortress-600/30'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        {/* Status */}
        <div className="p-4 border-t border-gray-800">
          <div className="card flex items-center gap-3 text-xs">
            <Activity className="w-4 h-4 text-fortress-400" />
            <div>
              <p className="text-gray-300 font-medium">System Online</p>
              <p className="text-gray-500">All services healthy</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
