import { useState } from 'react'
import { Search, Download, Filter, ArrowUpRight, ArrowDownRight, RefreshCcw } from 'lucide-react'

const mockTxns = [
  { id: 'TXN-001', type: 'debit', amount: -2.0, balance_after: 1471.2, description: 'KYC Verification — Kuda Bank', reference: 'kyc-abc123', created_at: '2024-12-01T10:30:00Z', pillar: 'NetraID' },
  { id: 'TXN-002', type: 'debit', amount: -500, balance_after: 1971.2, description: 'Sentinel Threat Scan — Paystack', reference: 'sentinel-def456', created_at: '2024-12-01T09:15:00Z', pillar: 'Sentinel' },
  { id: 'TXN-003', type: 'credit', amount: 500, balance_after: 2471.2, description: 'Top-up via Stripe', reference: 'pay-ghi789', created_at: '2024-11-30T16:45:00Z', pillar: 'Billing' },
  { id: 'TXN-004', type: 'debit', amount: -1.5, balance_after: 1971.2, description: 'Agent Deploy — Sales Agent', reference: 'deploy-jkl012', created_at: '2024-11-30T14:20:00Z', pillar: 'Agent Cloud' },
  { id: 'TXN-005', type: 'debit', amount: -0.5, balance_after: 1972.7, description: 'Remittance — Nigeria to Kenya', reference: 'afro-mno345', created_at: '2024-11-30T11:00:00Z', pillar: 'Afro-Pay' },
  { id: 'TXN-006', type: 'refund', amount: 2.0, balance_after: 1973.2, description: 'Refund — Failed KYC check', reference: 'ref-pqr678', created_at: '2024-11-29T09:30:00Z', pillar: 'NetraID' },
]

export default function Transactions() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  const filtered = mockTxns.filter((t) => {
    if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false
    if (filter === 'credits' && t.type !== 'credit') return false
    if (filter === 'debits' && t.type !== 'debit') return false
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white">Transactions</h1>
          <p className="text-gray-400 mt-1">Complete ledger of all credit movements</p>
        </div>
        <button className="btn-secondary flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transactions..."
            className="w-full bg-gray-800 border border-gray-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-fortress-500 transition-colors"
          />
        </div>
        <div className="flex bg-gray-800 rounded-xl border border-gray-700 p-1">
          {['all', 'credits', 'debits'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                filter === f ? 'bg-fortress-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Type</th>
              <th className="text-left text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Description</th>
              <th className="text-left text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Pillar</th>
              <th className="text-left text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Reference</th>
              <th className="text-right text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Amount</th>
              <th className="text-right text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Balance</th>
              <th className="text-right text-xs text-gray-400 uppercase tracking-wider py-3 px-4">Date</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
                <td className="py-3 px-4">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    t.type === 'credit' ? 'bg-fortress-500/20' : t.type === 'refund' ? 'bg-amber-500/20' : 'bg-red-500/20'
                  }`}>
                    {t.type === 'credit' ? (
                      <ArrowDownRight className="w-4 h-4 text-fortress-400" />
                    ) : t.type === 'refund' ? (
                      <RefreshCcw className="w-4 h-4 text-amber-400" />
                    ) : (
                      <ArrowUpRight className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-white">{t.description}</td>
                <td className="py-3 px-4">
                  <span className="text-xs px-2 py-1 rounded-full bg-gray-800 text-gray-300">{t.pillar}</span>
                </td>
                <td className="py-3 px-4 text-xs font-mono text-gray-400">{t.reference}</td>
                <td className={`py-3 px-4 text-right font-mono text-sm ${t.amount >= 0 ? 'text-fortress-400' : 'text-red-400'}`}>
                  {t.amount >= 0 ? '+' : ''}{t.amount}
                </td>
                <td className="py-3 px-4 text-right font-mono text-sm text-gray-300">
                  {t.balance_after.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td className="py-3 px-4 text-right text-xs text-gray-400">
                  {new Date(t.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
