import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  register: (data) => api.post('/auth/register/', data),
  logout: () => api.post('/auth/logout/'),
  refreshToken: (token) => api.post('/auth/refresh/', { refresh: token }),
  getProfile: () => api.get('/profile/'),
  updateProfile: (data) => api.put('/profile/update/', data),
  changePassword: (data) => api.post('/auth/password-change/', data),
};

// Trading API
export const tradingAPI = {
  getSymbols: () => api.get('/trading/symbols/'),
  getTrades: (params) => api.get('/trading/trades/', { params }),
  createTrade: (data) => api.post('/trading/trades/create/', data),
  closeTrade: (tradeId) => api.post(`/trading/trades/${tradeId}/close/`),
  getOrders: () => api.get('/trading/orders/'),
  createOrder: (data) => api.post('/trading/orders/create/', data),
  cancelOrder: (orderId) => api.post(`/trading/orders/${orderId}/cancel/`),
  getPositions: () => api.get('/trading/positions/'),
  getPortfolio: () => api.get('/trading/portfolio/'),
  getTradeHistory: () => api.get('/trading/history/'),
};

// Signals API
export const signalsAPI = {
  getSignals: (params) => api.get('/signals/', { params }),
  getSignal: (id) => api.get(`/signals/${id}/`),
  generateSignal: (data) => api.post('/signals/generate/', data),
  getActiveSignals: () => api.get('/signals/active/'),
  getConfluenceScores: (params) => api.get('/signals/confluence/', { params }),
};

// Risk API
export const riskAPI = {
  getRiskParameters: () => api.get('/risk/parameters/'),
  calculatePositionSize: (data) => api.post('/risk/position-sizing/', data),
  getDrawdownStatus: () => api.get('/risk/drawdown/status/'),
  getRiskDashboard: () => api.get('/risk/dashboard/'),
  getRiskAlerts: () => api.get('/risk/alerts/'),
  getDailyPerformance: (params) => api.get('/risk/daily-performance/', { params }),
};

// Indicators API
export const indicatorsAPI = {
  getTimeframes: () => api.get('/indicators/timeframes/'),
  getIndicators: (params) => api.get('/indicators/', { params }),
  getIndicatorValues: (params) => api.get('/indicators/values/', { params }),
  calculateIndicators: (data) => api.post('/indicators/calculate/', data),
};

// Payments API
export const paymentsAPI = {
  getGateways: () => api.get('/payments/gateways/'),
  getTransactions: (params) => api.get('/payments/transactions/', { params }),
  deposit: (data) => api.post('/payments/deposit/', data),
  withdraw: (data) => api.post('/payments/withdraw/', data),
  getKYCStatus: () => api.get('/payments/kyc/status/'),
  submitKYC: (data) => api.post('/payments/kyc/submit/', data),
  getPaymentMethods: () => api.get('/payments/methods/'),
};

// Expert Advisors API
export const easAPI = {
  getEAs: () => api.get('/eas/'),
  getEA: (id) => api.get(`/eas/${id}/`),
  createEA: (data) => api.post('/eas/create/', data),
  generateCode: (data) => api.post('/eas/generate-code/', data),
  backtestEA: (eaId) => api.post(`/eas/${eaId}/backtest/`),
  deployEA: (eaId) => api.post(`/eas/${eaId}/deploy/`),
};

// Market Data API
export const marketAPI = {
  getLivePrices: () => api.get('/market/live/'),
  getMarketData: (params) => api.get('/market/', { params }),
  getEconomicCalendar: (params) => api.get('/market/calendar/', { params }),
  getSentiment: (params) => api.get('/market/sentiment/', { params }),
  getOverview: () => api.get('/market/overview/'),
};

// MCP Integration API
export const mcpAPI = {
  getServers: () => api.get('/mcp/servers/'),
  getTools: (params) => api.get('/mcp/tools/', { params }),
  callTool: (data) => api.post('/mcp/call/', data),
  getHealth: () => api.get('/mcp/health/'),
};

// Notifications API
export const notificationsAPI = {
  getNotifications: (params) => api.get('/notifications/', { params }),
  markAsRead: (id) => api.post(`/notifications/${id}/read/`),
  markAllAsRead: () => api.post('/notifications/read-all/'),
  getUnreadCount: () => api.get('/notifications/unread-count/'),
  getPreferences: () => api.get('/notifications/preferences/'),
  updatePreferences: (data) => api.put('/notifications/preferences/', data),
};

// Analytics API
export const analyticsAPI = {
  getPerformance: () => api.get('/analytics/performance/'),
  getRiskAnalytics: () => api.get('/analytics/risk/'),
  getSignalAnalytics: () => api.get('/analytics/signals/'),
};

export default api;
