import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });
        localStorage.setItem('access_token', data.access);
        if (data.refresh) {
          localStorage.setItem('refresh_token', data.refresh);
        }
        api.defaults.headers.common.Authorization = `Bearer ${data.access}`;
        processQueue(null, data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  register: (data) => api.post('/auth/register/', data),
  logout: (refreshToken) => api.post('/auth/logout/', { refresh: refreshToken }),
  refreshToken: (token) => api.post('/auth/refresh/', { refresh: token }),
  getProfile: () => api.get('/profile/'),
  updateProfile: (data) => api.put('/profile/update/', data),
  changePassword: (data) => api.post('/auth/password-change/', data),
  mfaSetup: () => api.get('/auth/mfa/setup/'),
  mfaEnable: (code) => api.post('/auth/mfa/setup/', { code }),
  mfaDisable: (code) => api.post('/auth/mfa/disable/', { code }),
  getSessions: () => api.get('/sessions/'),
  deleteSession: (id) => api.delete(`/sessions/${id}/`),
  getMT5Connection: () => api.get('/mt5/connection/'),
  connectMT5: (data) => api.post('/mt5/connection/', data),
};

export const tradingAPI = {
  getSymbols: () => api.get('/trading/symbols/'),
  getTrades: (params) => api.get('/trading/trades/', { params }),
  createTrade: (data) => api.post('/trading/trades/create/', data),
  closeTrade: (tradeId) => api.post(`/trading/trades/${tradeId}/close/`),
  getOrders: (params) => api.get('/trading/orders/', { params }),
  createOrder: (data) => api.post('/trading/orders/create/', data),
  cancelOrder: (orderId) => api.post(`/trading/orders/${orderId}/cancel/`),
  getPositions: () => api.get('/trading/positions/'),
  getPortfolio: () => api.get('/trading/portfolio/'),
};

export const signalsAPI = {
  getSignals: (params) => api.get('/signals/', { params }),
  getSignal: (id) => api.get(`/signals/${id}/`),
  getActiveSignals: () => api.get('/signals/active/'),
  getConfluenceScores: (params) => api.get('/signals/confluence/', { params }),
  generateSignal: (data) => api.post('/signals/generate/', data),
};

export const riskAPI = {
  getRiskParameters: () => api.get('/risk/parameters/'),
  calculatePositionSize: (data) => api.post('/risk/position-sizing/', data),
  getDrawdownStatus: () => api.get('/risk/drawdown/status/'),
  getRiskDashboard: () => api.get('/risk/dashboard/'),
  getRiskAlerts: () => api.get('/risk/alerts/'),
  getDailyPerformance: (params) => api.get('/risk/daily-performance/', { params }),
};

export const indicatorsAPI = {
  getTimeframes: () => api.get('/indicators/timeframes/'),
  getIndicators: (params) => api.get('/indicators/', { params }),
  getIndicatorValues: (params) => api.get('/indicators/values/', { params }),
  calculateIndicators: (data) => api.post('/indicators/calculate/', data),
};

export const paymentsAPI = {
  getGateways: () => api.get('/payments/gateways/'),
  getTransactions: (params) => api.get('/payments/transactions/', { params }),
  getTransaction: (id) => api.get(`/payments/transactions/${id}/`),
  initializeDeposit: (data) => api.post('/payments/deposit/', data),
  verifyDeposit: (reference) => api.post('/payments/verify/', { reference }),
  createWithdrawal: (data) => api.post('/payments/withdraw/', data),
  getKYCStatus: () => api.get('/payments/kyc/status/'),
  submitKYC: (data) => api.post('/payments/kyc/submit/', data),
  getPaymentMethods: () => api.get('/payments/methods/'),
  createPaymentMethod: (data) => api.post('/payments/methods/create/', data),
  reconcile: (data) => api.post('/payments/reconcile/', data),
  getPaymentCallback: (params) => api.get('/payments/callback/', { params }),
};

export const easAPI = {
  getEAs: () => api.get('/eas/'),
  getEA: (id) => api.get(`/eas/${id}/`),
  createEA: (data) => api.post('/eas/create/', data),
  generateCode: (data) => api.post('/eas/generate-code/', data),
  backtestEA: (eaId) => api.post(`/eas/${eaId}/backtest/`),
  deployEA: (eaId) => api.post(`/eas/${eaId}/deploy/`),
  deleteEA: (eaId) => api.delete(`/eas/${eaId}/`),
};

export const marketAPI = {
  getLivePrices: () => api.get('/market/live/'),
  getMarketData: (params) => api.get('/market/', { params }),
  getEconomicCalendar: (params) => api.get('/market/calendar/', { params }),
  getSentiment: (params) => api.get('/market/sentiment/', { params }),
  getOverview: () => api.get('/market/overview/'),
};

export const analyticsAPI = {
  getPerformance: () => api.get('/analytics/performance/'),
  getRiskAnalytics: () => api.get('/analytics/risk/'),
  getSignalAnalytics: () => api.get('/analytics/signals/'),
};

export const backtestingAPI = {
  getBacktests: () => api.get('/backtesting/'),
  getBacktest: (id) => api.get(`/backtesting/${id}/`),
  runBacktest: (data) => api.post('/backtesting/run/', data),
};

export const referralsAPI = {
  getReferrals: () => api.get('/referrals/'),
  createReferral: () => api.post('/referrals/create/'),
  applyReferral: (code) => api.post('/referrals/apply/', { code }),
  getStats: () => api.get('/referrals/stats/'),
};

export const notificationsAPI = {
  getNotifications: (params) => api.get('/notifications/', { params }),
  markAsRead: (id) => api.post(`/notifications/${id}/read/`),
  markAllAsRead: () => api.post('/notifications/read-all/'),
  getUnreadCount: () => api.get('/notifications/unread-count/'),
  getPreferences: () => api.get('/notifications/preferences/'),
  updatePreferences: (data) => api.put('/notifications/preferences/', data),
};

export default api;
