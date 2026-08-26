const API_BASE = '/api/v1'

export interface CreditBalance {
  balance: number
  currency: string
  credit_rate_usd: number
  total_earned: number
  total_spent: number
  low_balance_threshold: number
  auto_topup_enabled: boolean
}

export interface Transaction {
  id: string
  type: string
  amount: number
  balance_after: number
  description: string
  reference: string | null
  created_at: string
}

export interface Agent {
  id: string
  name: string
  slug: string
  pillar: string
  credit_cost_per_task: number
}

export interface UsageStats {
  total_executions: number
  total_credits_charged: number
  executions_by_agent: Record<string, number>
  executions_today: number
}

export interface DashboardData {
  total_revenue_usd: number
  total_cost_usd: number
  gross_margin_pct: number
  total_credits_consumed: number
  active_clients: number
  total_wallet_balance: number
}

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('fortress_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }
  return response.json()
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      fetcher<{ access_token: string; client_id: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (data: { email: string; password: string; name: string }) =>
      fetcher<{ client_id: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  billing: {
    getBalance: () => fetcher<CreditBalance>('/billing/balance'),
    getTransactions: (limit = 50) =>
      fetcher<Transaction[]>(`/billing/transactions?limit=${limit}`),
    topUp: (amount_usd: number, provider: string) =>
      fetcher('/billing/topup', {
        method: 'POST',
        body: JSON.stringify({ amount_usd, provider }),
      }),
    configureAutoTopup: (enabled: boolean, amount: number, trigger_at: number) =>
      fetcher('/billing/auto-topup', {
        method: 'PUT',
        body: JSON.stringify({ enabled, amount, trigger_at }),
      }),
  },
  metering: {
    getAgents: () => fetcher<Agent[]>('/metering/agents'),
    getUsage: () => fetcher<UsageStats>('/metering/usage'),
  },
  admin: {
    getDashboard: () => fetcher<DashboardData>('/admin/dashboard'),
  },
}
