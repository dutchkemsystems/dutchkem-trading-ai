import { useState } from 'react'
import { Wallet as WalletIcon, CreditCard, Zap, ArrowUpRight, ArrowDownRight, Settings } from 'lucide-react'

const mockWallet = {
  balance: 1_473.20,
  credit_rate_usd: 0.10,
  total_earned: 4_200.00,
  total_spent: 2_726.80,
  auto_topup_enabled: true,
  auto_topup_amount: 500,
  auto_topup_trigger: 100,
}

const paymentProviders = [
  { id: 'paystack', name: 'Paystack', currencies: ['NGN'], icon: '🇳🇬' },
  { id: 'flutterwave', name: 'Flutterwave', currencies: ['NGN', 'GHS', 'KES'], icon: '🌍' },
  { id: 'stripe', name: 'Stripe', currencies: ['USD', 'EUR', 'GBP'], icon: '💳' },
]

export default function Wallet() {
  const [wallet] = useState(mockWallet)
  const [topUpAmount, setTopUpAmount] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('stripe')

  const creditValue = wallet.balance * wallet.credit_rate_usd

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-display font-bold text-white">Agentic Fuel Wallet</h1>
        <p className="text-gray-400 mt-1">Manage your credits — 1 Credit = $0.10 USD pegged to live FX rates</p>
      </div>

      {/* Balance Card */}
      <div className="card bg-gradient-to-br from-fortress-900/80 to-fortress-950/80 border-fortress-700/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-fortress-300 uppercase tracking-wider">Available Fuel</p>
            <p className="text-5xl font-mono font-bold text-white mt-2">
              {wallet.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })} <span className="text-xl text-fortress-400">Credits</span>
            </p>
            <p className="text-lg text-fortress-300 mt-1 font-mono">
              ≈ ${creditValue.toLocaleString(undefined, { minimumFractionDigits: 2 })} USD
            </p>
          </div>
          <div className="w-20 h-20 rounded-2xl bg-fortress-500/20 flex items-center justify-center">
            <Zap className="w-10 h-10 text-fortress-400" />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-8">
          <div className="p-4 rounded-xl bg-black/20">
            <p className="text-xs text-fortress-300/70 uppercase tracking-wider">Total Earned</p>
            <p className="text-lg font-mono text-white mt-1">${wallet.total_earned.toLocaleString()}</p>
          </div>
          <div className="p-4 rounded-xl bg-black/20">
            <p className="text-xs text-fortress-300/70 uppercase tracking-wider">Total Spent</p>
            <p className="text-lg font-mono text-white mt-1">${wallet.total_spent.toLocaleString()}</p>
          </div>
          <div className="p-4 rounded-xl bg-black/20">
            <p className="text-xs text-fortress-300/70 uppercase tracking-wider">Credit Rate</p>
            <p className="text-lg font-mono text-white mt-1">1 Credit = ${wallet.credit_rate_usd}</p>
          </div>
        </div>
      </div>

      {/* Top Up */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-display font-semibold text-white mb-4">Top Up Fuel</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-400 block mb-1">Amount (USD)</label>
              <input
                type="number"
                value={topUpAmount}
                onChange={(e) => setTopUpAmount(e.target.value)}
                placeholder="100.00"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white font-mono focus:outline-none focus:border-fortress-500 transition-colors"
              />
              {topUpAmount && (
                <p className="text-sm text-gray-400 mt-1">
                  You'll receive <span className="text-fortress-400 font-mono">{(parseFloat(topUpAmount) / 0.10).toFixed(0)} credits</span>
                </p>
              )}
            </div>

            <div>
              <label className="text-sm text-gray-400 block mb-2">Payment Provider</label>
              <div className="space-y-2">
                {paymentProviders.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedProvider(p.id)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all ${
                      selectedProvider === p.id
                        ? 'border-fortress-500 bg-fortress-500/10'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{p.icon}</span>
                      <span className="text-sm font-medium text-white">{p.name}</span>
                    </div>
                    <span className="text-xs text-gray-400">{p.currencies.join(', ')}</span>
                  </button>
                ))}
              </div>
            </div>

            <button className="btn-primary w-full flex items-center justify-center gap-2">
              <CreditCard className="w-4 h-4" />
              Top Up Now
            </button>
          </div>
        </div>

        {/* Auto Top-Up Settings */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-white">Auto Top-Up</h2>
            <Settings className="w-4 h-4 text-gray-500" />
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-xl bg-gray-800/50">
              <div>
                <p className="text-sm font-medium text-white">Auto Top-Up</p>
                <p className="text-xs text-gray-400">Automatically replenish when low</p>
              </div>
              <div className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${wallet.auto_topup_enabled ? 'bg-fortress-600' : 'bg-gray-700'}`}>
                <div className={`w-5 h-5 rounded-full bg-white absolute top-0.5 transition-transform ${wallet.auto_topup_enabled ? 'translate-x-6' : 'translate-x-0.5'}`} />
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-xl bg-gray-800/30">
                <span className="text-sm text-gray-400">Trigger At</span>
                <span className="font-mono text-sm text-white">{wallet.auto_topup_trigger} credits</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-gray-800/30">
                <span className="text-sm text-gray-400">Top-Up Amount</span>
                <span className="font-mono text-sm text-white">${wallet.auto_topup_amount}</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-gray-800/30">
                <span className="text-sm text-gray-400">Saved Card</span>
                <span className="text-sm text-fortress-400">**** 4242</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <p className="text-xs text-amber-400">
                When your balance drops below {wallet.auto_topup_trigger} credits, we'll automatically charge ${wallet.auto_topup_amount} to your saved card.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* FX Peg Info */}
      <div className="card">
        <h2 className="font-display font-semibold text-white mb-4">FX Hedging & Credit Peg</h2>
        <div className="grid grid-cols-4 gap-4">
          {[
            { pair: 'USD/NGN', rate: '₦1,580.25', trend: 'up' },
            { pair: 'USD/GHS', rate: 'GH₵15.42', trend: 'down' },
            { pair: 'USD/KES', rate: 'KSh153.80', trend: 'up' },
            { pair: 'USD/ZAR', rate: 'R18.45', trend: 'down' },
          ].map((fx) => (
            <div key={fx.pair} className="p-4 rounded-xl bg-gray-800/30 border border-gray-800">
              <p className="text-xs text-gray-400 uppercase tracking-wider">{fx.pair}</p>
              <p className="text-lg font-mono text-white mt-1">{fx.rate}</p>
              <div className={`flex items-center gap-1 text-xs mt-1 ${fx.trend === 'up' ? 'text-fortress-400' : 'text-red-400'}`}>
                {fx.trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                Updated 2m ago
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
