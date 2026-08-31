import { configureStore } from '@reduxjs/toolkit';
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { authAPI, tradingAPI, signalsAPI, riskAPI, analyticsAPI } from './services/api';
import * as SecureStore from 'expo-secure-store';

export const loginUser = createAsyncThunk('auth/login', async (credentials, { rejectWithValue }) => {
  try {
    const { data } = await authAPI.login(credentials);
    await SecureStore.setItemAsync('access_token', data.access);
    await SecureStore.setItemAsync('refresh_token', data.refresh);
    return data;
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Login failed');
  }
});

export const logoutUser = createAsyncThunk('auth/logout', async () => {
  try {
    const refreshToken = await SecureStore.getItemAsync('refresh_token');
    if (refreshToken) await authAPI.logout(refreshToken);
  } catch {}
  await SecureStore.deleteItemAsync('access_token');
  await SecureStore.deleteItemAsync('refresh_token');
});

export const fetchProfile = createAsyncThunk('auth/fetchProfile', async (_, { rejectWithValue }) => {
  try {
    const { data } = await authAPI.getProfile();
    return data;
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to fetch profile');
  }
});

export const fetchPortfolio = createAsyncThunk('trading/fetchPortfolio', async () => {
  const { data } = await tradingAPI.getPortfolio();
  return data;
});

export const fetchPositions = createAsyncThunk('trading/fetchPositions', async () => {
  const { data } = await tradingAPI.getPositions();
  return data.results || data;
});

export const fetchActiveSignals = createAsyncThunk('signals/fetchActive', async () => {
  const { data } = await signalsAPI.getActiveSignals();
  return data.results || data;
});

export const fetchRiskDashboard = createAsyncThunk('risk/fetchDashboard', async () => {
  const { data } = await riskAPI.getRiskDashboard();
  return data;
});

export const fetchPerformance = createAsyncThunk('analytics/fetchPerformance', async () => {
  const { data } = await analyticsAPI.getPerformance();
  return data;
});

const authSlice = createSlice({
  name: 'auth',
  initialState: { user: null, isAuthenticated: false, loading: false, error: null },
  reducers: { clearError: (s) => { s.error = null; } },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (s) => { s.loading = true; s.error = null; })
      .addCase(loginUser.fulfilled, (s, a) => { s.loading = false; s.user = a.payload.user; s.isAuthenticated = true; })
      .addCase(loginUser.rejected, (s, a) => { s.loading = false; s.error = a.payload; })
      .addCase(logoutUser.fulfilled, (s) => { s.user = null; s.isAuthenticated = false; })
      .addCase(fetchProfile.fulfilled, (s, a) => { s.user = a.payload; });
  },
});

const tradingSlice = createSlice({
  name: 'trading',
  initialState: { positions: [], portfolio: null, loading: false },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPortfolio.fulfilled, (s, a) => { s.portfolio = a.payload; s.loading = false; })
      .addCase(fetchPortfolio.pending, (s) => { s.loading = true; })
      .addCase(fetchPositions.fulfilled, (s, a) => { s.positions = a.payload; s.loading = false; })
      .addCase(fetchPositions.pending, (s) => { s.loading = true; });
  },
});

const signalsSlice = createSlice({
  name: 'signals',
  initialState: { activeSignals: [], loading: false },
  extraReducers: (builder) => {
    builder
      .addCase(fetchActiveSignals.fulfilled, (s, a) => { s.activeSignals = a.payload; s.loading = false; })
      .addCase(fetchActiveSignals.pending, (s) => { s.loading = true; });
  },
});

const riskSlice = createSlice({
  name: 'risk',
  initialState: { dashboard: null, loading: false },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRiskDashboard.fulfilled, (s, a) => { s.dashboard = a.payload; s.loading = false; })
      .addCase(fetchRiskDashboard.pending, (s) => { s.loading = true; });
  },
});

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState: { performance: null, loading: false },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPerformance.fulfilled, (s, a) => { s.performance = a.payload; s.loading = false; })
      .addCase(fetchPerformance.pending, (s) => { s.loading = true; });
  },
});

export const store = configureStore({
  reducer: {
    auth: authSlice.reducer,
    trading: tradingSlice.reducer,
    signals: signalsSlice.reducer,
    risk: riskSlice.reducer,
    analytics: analyticsSlice.reducer,
  },
  middleware: (getDefault) => getDefault({ serializableCheck: false }),
});

export default store;
