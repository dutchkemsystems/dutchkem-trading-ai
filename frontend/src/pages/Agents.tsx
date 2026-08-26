import { useState } from 'react'
import { Bot, Play, Pause, Activity, Zap, Shield, Globe, CreditCard, Brain } from 'lucide-react'

const agents = [
  { name: 'KYC Agent', slug: 'kyc-agent', pillar: 'NetraID', cost: 2.0, status: 'active', executions: 10_500, icon: CreditCard, color: 'from-purple-500 to-violet-600' },
  { name: 'Sentinel Recon', slug: 'sentinel-recon', pillar: 'Sentinel', cost: 500, status: 'active', executions: 892, icon: Shield, color: 'from-red-500 to-rose-600' },
  { name: 'Sales Agent', slug: 'sales-agent', pillar: 'Agent Cloud', cost: 1.5, status: 'active', executions: 8_200, icon: Zap, color: 'from-blue-500 to-indigo-600' },
  { name: 'Remittance Router', slug: 'afropay-router', pillar: 'Afro-Pay', cost: 0.5, status: 'active', executions: 12_847, icon: Globe, color: 'from-emerald-500 to-teal-600' },
  { name: 'TrustNode Router', slug: 'trustnode-router', pillar: 'TrustNode', cost: 0.01, status: 'active', executions: 35_000, icon: Brain, color: 'from-amber-500 to-orange-600' },
  { name: 'Loan Recovery', slug: 'loan-recovery', pillar: 'Agent Cloud', cost: 1.5, status: 'paused', executions: 3_200, icon: Bot, color: 'from-pink-500 to-rose-600' },
  { name: 'Deepfake Detection', slug: 'deepfake-detect', pillar: 'Sentinel', cost: 500, status: 'active', executions: 450, icon: Shield, color: 'from-red-600 to-red-800' },
  { name: 'Phishing Takedown', slug: 'phishing-takedown', pillar: 'Sentinel', cost: 500, status: 'active', executions: 320, icon: Shield, color: 'from-red-400 to-red-600' },
]

export default function Agents() {
  const [search, setSearch] = useState('')

  const filtered = agents.filter(
    (a) => a.name.toLowerCase().includes(search.toLowerCase()) || a.pillar.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white">Agent Registry</h1>
          <p className="text-gray-400 mt-1">All agents across the Fortress platform — metered by Agentic Fuel</p>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4">
        <div className="stat-card">
          <p className="stat-label">Total Agents</p>
          <p className="stat-value text-fortress-400">{agents.length}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Active</p>
          <p className="stat-value text-emerald-400">{agents.filter((a) => a.status === 'active').length}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Total Executions</p>
          <p className="stat-value text-amber-400">{agents.reduce((s, a) => s + a.executions, 0).toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Avg Cost/Task</p>
          <p className="stat-value text-blue-400">
            ${(agents.reduce((s, a) => s + a.cost, 0) / agents.length).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-2 gap-4">
        {filtered.map((agent) => {
          const Icon = agent.icon
          return (
            <div key={agent.slug} className="card-hover group">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${agent.color} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-display font-semibold text-white">{agent.name}</h3>
                    <p className="text-xs text-gray-400">{agent.pillar}</p>
                  </div>
                </div>
                <div className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  agent.status === 'active' ? 'bg-fortress-500/20 text-fortress-400' : 'bg-gray-700 text-gray-400'
                }`}>
                  {agent.status}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-6">
                <div>
                  <p className="text-xs text-gray-500 uppercase">Cost/Task</p>
                  <p className="font-mono text-sm text-white mt-0.5">
                    {agent.cost >= 1 ? `$${agent.cost}` : `$${agent.cost.toFixed(3)}`}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase">Executions</p>
                  <p className="font-mono text-sm text-white mt-0.5">{agent.executions.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase">Revenue</p>
                  <p className="font-mono text-sm text-fortress-400 mt-0.5">
                    ${(agent.executions * agent.cost * 0.10).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
