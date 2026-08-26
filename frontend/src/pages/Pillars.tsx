import { Globe, Shield, Bot, CreditCard, Brain, ArrowUpRight, ExternalLink } from 'lucide-react'

const pillars = [
  {
    id: 1,
    name: 'Afro-Pay',
    tagline: 'Web3 Remittance & Fintech',
    description: 'Target the $20B+ Nigerian and $100B+ African remittance corridors with stablecoin on/off-ramps, P2P transfers via WhatsApp/Telegram, and instant last-mile cash-out to mobile money.',
    features: ['USDT/USDC On/Off-Ramps', 'WhatsApp/Telegram P2P', 'M-Pesa & MoMo Integration', '0.5% Settlement Fee'],
    icon: Globe,
    color: 'from-emerald-500 to-teal-600',
    revenue: '$42.1k/mo',
    tam: '$100B+ African Remittance',
    status: 'live',
  },
  {
    id: 2,
    name: 'Sentinel Africa',
    tagline: 'Cybersecurity & SOC-as-a-Service',
    description: 'Autonomous SOC for SMEs using multi-agent architecture for network defense, deepfake detection, and phishing takedowns. $500/month per active threat neutralized.',
    features: ['Recon/Simulation/Response Agents', 'Deepfake Detection', 'Phishing Takedowns', 'Autonomous SOC'],
    icon: Shield,
    color: 'from-red-500 to-rose-600',
    revenue: '$38.9k/mo',
    tam: '$1.44B by 2031',
    status: 'live',
  },
  {
    id: 3,
    name: 'African Agent Cloud',
    tagline: 'Vertical AI Workforce',
    description: '"System 2" agents that understand local nuances — Swahili, Yoruba, local accounting rules. Marketplace to deploy Sales, KYC/AML, HR, and E-commerce agents.',
    features: ['Sales & KYC Agents', 'HR & E-commerce Agents', 'Loan Recovery Agent', 'Local Language Support'],
    icon: Bot,
    color: 'from-blue-500 to-indigo-600',
    revenue: '$31.2k/mo',
    tam: '$1.1T Mobile Money',
    status: 'live',
  },
  {
    id: 4,
    name: 'NetraID',
    tagline: 'Digital Identity & Compliance',
    description: 'Built for NDPA (Nigeria) and POPIA (South Africa). AI-driven biometric verification, liveness checks countering 27% rejection rates, blockchain-backed identity tokens.',
    features: ['Biometric Verification', 'Liveness Detection', 'Blockchain Identity Tokens', 'NDPA & POPIA Compliance'],
    icon: CreditCard,
    color: 'from-purple-500 to-violet-600',
    revenue: '$21.0k/mo',
    tam: '$2.5B Identity Market',
    status: 'live',
  },
  {
    id: 5,
    name: 'TrustNode',
    tagline: 'Open-Weight AI Abstraction Layer',
    description: 'Middleware to switch between OpenAI, Claude, or local open-weight models seamlessly. Prevents vendor lock-in and USD-based AI subscription traps.',
    features: ['Multi-Model Routing', 'Cost Optimization', 'Fallback Chains', 'Quality Monitoring'],
    icon: Brain,
    color: 'from-amber-500 to-orange-600',
    revenue: '$14.0k/mo',
    tam: 'AI Infrastructure Layer',
    status: 'live',
  },
]

export default function Pillars() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold text-white">Platform Pillars</h1>
        <p className="text-gray-400 mt-1">5 revenue-generating modules — all metered through Agentic Fuel</p>
      </div>

      {/* Revenue Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card bg-gradient-to-br from-fortress-900/80 to-fortress-950/80 border-fortress-700/30">
          <p className="text-sm text-fortress-300">Combined Revenue</p>
          <p className="text-3xl font-mono font-bold text-white mt-1">$147.3k/mo</p>
        </div>
        <div className="card bg-gradient-to-br from-emerald-900/50 to-emerald-950/50 border-emerald-700/30">
          <p className="text-sm text-emerald-300">Active Pillars</p>
          <p className="text-3xl font-mono font-bold text-white mt-1">5/5</p>
        </div>
        <div className="card bg-gradient-to-br from-amber-900/50 to-amber-950/50 border-amber-700/30">
          <p className="text-sm text-amber-300">Combined TAM</p>
          <p className="text-3xl font-mono font-bold text-white mt-1">$105B+</p>
        </div>
      </div>

      {/* Pillar Cards */}
      <div className="space-y-4">
        {pillars.map((pillar) => {
          const Icon = pillar.icon
          return (
            <div key={pillar.id} className="card-hover group">
              <div className="flex items-start gap-6">
                <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${pillar.color} flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform`}>
                  <Icon className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-display font-bold text-white">{pillar.name}</h2>
                    <span className="px-2 py-0.5 rounded-full bg-fortress-500/20 text-fortress-400 text-xs font-medium">
                      P{pillar.id}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium capitalize">
                      {pillar.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{pillar.tagline}</p>
                  <p className="text-sm text-gray-300 mt-2 leading-relaxed">{pillar.description}</p>

                  <div className="flex items-center gap-6 mt-4">
                    <div>
                      <p className="text-xs text-gray-500">Revenue</p>
                      <p className="font-mono text-sm text-fortress-400">{pillar.revenue}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">TAM</p>
                      <p className="font-mono text-sm text-amber-400">{pillar.tam}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mt-4">
                    {pillar.features.map((f) => (
                      <span key={f} className="px-2.5 py-1 rounded-lg bg-gray-800/50 text-xs text-gray-300 border border-gray-700/50">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
