import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
  async (config) => {
    const token = await SecureStore.getItemAsync('access_token');
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

      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (!refreshToken) {
        await SecureStore.deleteItemAsync('access_token');
        await SecureStore.deleteItemAsync('refresh_token');
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });
        await SecureStore.setItemAsync('access_token', data.access);
        if (data.refresh) {
          await SecureStore.setItemAsync('refresh_token', data.refresh);
        }
        api.defaults.headers.common.Authorization = `Bearer ${data.access}`;
        processQueue(null, data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        await SecureStore.deleteItemAsync('access_token');
        await SecureStore.deleteItemAsync('refresh_token');
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
  getProfile: () => api.get('/profile/'),
  updateProfile: (data) => api.put('/profile/update/', data),
};

export const tradingAPI = {
  getPositions: () => api.get('/trading/positions/'),
  getPortfolio: () => api.get('/trading/portfolio/'),
  getTrades: (params) => api.get('/trading/trades/', { params }),
  getSymbols: () => api.get('/trading/symbols/'),
  createOrder: (data) => api.post('/trading/orders/create/', data),
};

export const signalsAPI = {
  getActiveSignals: () => api.get('/signals/active/'),
  getConfluenceScores: (params) => api.get('/signals/confluence/', { params }),
};

export const riskAPI = {
  getRiskDashboard: () => api.get('/risk/dashboard/'),
  getDrawdownStatus: () => api.get('/risk/drawdown/status/'),
};

export const analyticsAPI = {
  getPerformance: () => api.get('/analytics/performance/'),
  getRiskAnalytics: () => api.get('/analytics/risk/'),
};

export const marketAPI = {
  getLivePrices: () => api.get('/market/live/'),
  getOverview: () => api.get('/market/overview/'),
};

export default api;
