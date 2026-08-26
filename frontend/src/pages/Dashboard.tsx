import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Zap,
  Users,
  DollarSign,
  Activity,
  Shield,
  CreditCard,
  Globe,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { api, type DashboardData } from '../lib/api'

const mockDashboard: DashboardData = {
  total_revenue_usd: 147_320.50,
  total_cost_usd: 51_562.18,
  gross_margin_pct: 65.0,
  total_credits_consumed: 1_473_205,
  active_clients: 847,
  total_wallet_balance: 89_410.25,
}

const pillars = [
  { name: 'Afro-Pay', revenue: 42_180, txns: 12_847, color: 'from-emerald-500 to-teal-600', icon: Globe },
  { name: 'Sentinel Africa', revenue: 38_900, txns: 892, color: 'from-red-500 to-rose-600', icon: Shield },
  { name: 'Agent Cloud', revenue: 31_240, txns: 20_827, color: 'from-blue-500 to-indigo-600', icon: Zap },
  { name: 'NetraID', revenue: 21_000, txns: 10_500, color: 'from-purple-500 to-violet-600', icon: CreditCard },
  { name: 'TrustNode', revenue: 14_000, txns: 35_000, color: 'from-amber-500 to-orange-600', icon: Activity },
]

const recentActivity = [
  { id: 1, client: 'Kuda Bank', action: 'KYC verification', credits: -2.0, time: '2m ago', status: 'success' },
  { id: 2, client: 'Paystack', action: 'Threat scan', credits: -500, time: '5m ago', status: 'success' },
  { id: 3, client: 'Flutterwave', action: 'Agent deploy', credits: -1.5, time: '12m ago', status: 'success' },
  { id: 4, client: 'MTN Nigeria', action: 'Remittance', credits: -0.5, time: '18m ago', status: 'success' },
  { id: 5, client: 'Safaricom', action: 'Identity verify', credits: -2.0, time: '25m ago', status: 'pending' },
]

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>(mockDashboard)

  useEffect(() => {
    api.admin.getDashboard().then(setData).catch(() => {})
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white">
          Fortress Command Center
        </h1>
        <p className="text-gray-400 mt-1">
          Real-time platform metrics for Dutchkem Ventures
        </p>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total Revenue"
          value={`$${data.total_revenue_usd.toLocaleString()}`}
          change={12.4}
          color="text-fortress-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Gross Margin"
          value={`${data.gross_margin_pct}%`}
          change={2.1}
          color="text-emerald-400"
        />
        <StatCard
          icon={Zap}
          label="Fuel Consumed"
          value={`${(data.total_credits_consumed / 1_000_000).toFixed(1)}M`}
          change={8.7}
          color="text-amber-400"
        />
        <StatCard
          icon={Users}
          label="Active Clients"
          value={data.active_clients.toLocaleString()}
          change={15.3}
          color="text-blue-400"
        />
      </div>

      {/* Pillar Revenue Grid */}
      <div className="card">
        <h2 className="font-display font-semibold text-white mb-4">Revenue by Pillar</h2>
        <div className="grid grid-cols-5 gap-3">
          {pillars.map((p) => {
            const Icon = p.icon
            return (
              <div key={p.name} className="card-hover group cursor-pointer">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${p.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <p className="text-sm text-gray-400">{p.name}</p>
                <p className="text-xl font-bold font-mono text-white">${(p.revenue / 1000).toFixed(1)}k</p>
                <p className="text-xs text-gray-500 mt-1">{p.txns.toLocaleString()} txns</p>
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Fuel Gauge */}
        <div className="card col-span-1">
          <h2 className="font-display font-semibold text-white mb-4">Agentic Fuel Pool</h2>
          <div className="space-y-4">
            <div className="text-center">
              <p className="text-5xl font-mono font-bold text-fortress-400">$89.4k</p>
              <p className="text-sm text-gray-400 mt-1">Total client balance</p>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Credit Rate</span>
                <span className="font-mono text-white">1 Credit = $0.10</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">FX Hedging</span>
                <span className="text-fortress-400 font-medium">Active</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Auto-Topup</span>
                <span className="text-amber-400 font-medium">847 clients</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card col-span-2">
          <h2 className="font-display font-semibold text-white mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {recentActivity.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-3 rounded-xl bg-gray-800/30 border border-gray-800">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${a.status === 'success' ? 'bg-fortress-400' : 'bg-amber-400'}`} />
                  <div>
                    <p className="text-sm font-medium text-white">{a.client}</p>
                    <p className="text-xs text-gray-500">{a.action}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm text-gray-300">{a.credits}</p>
                  <p className="text-xs text-gray-500">{a.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  change,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  change: number
  color: string
}) {
  const positive = change >= 0
  return (
    <div className="card-hover">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl bg-gray-800 flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <div className={`flex items-center gap-1 text-xs font-medium ${positive ? 'text-fortress-400' : 'text-red-400'}`}>
          {positive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(change)}%
        </div>
      </div>
      <p className="stat-label">{label}</p>
      <p className={`stat-value ${color}`}>{value}</p>
    </div>
  )
}
