import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { riskAPI } from '../../services/api';

export const fetchRiskParameters = createAsyncThunk(
  'risk/fetchParameters',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await riskAPI.getRiskParameters();
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch risk parameters');
    }
  }
);

export const fetchDrawdownStatus = createAsyncThunk(
  'risk/fetchDrawdown',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await riskAPI.getDrawdownStatus();
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch drawdown status');
    }
  }
);

export const fetchRiskDashboard = createAsyncThunk(
  'risk/fetchDashboard',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await riskAPI.getRiskDashboard();
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch risk dashboard');
    }
  }
);

export const fetchRiskAlerts = createAsyncThunk(
  'risk/fetchAlerts',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await riskAPI.getRiskAlerts();
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch risk alerts');
    }
  }
);

export const fetchDailyPerformance = createAsyncThunk(
  'risk/fetchDailyPerformance',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await riskAPI.getDailyPerformance(params);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch daily performance');
    }
  }
);

export const calculatePositionSize = createAsyncThunk(
  'risk/calculatePositionSize',
  async (data, { rejectWithValue }) => {
    try {
      const { data: result } = await riskAPI.calculatePositionSize(data);
      return result;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to calculate position size');
    }
  }
);

const riskSlice = createSlice({
  name: 'risk',
  initialState: {
    riskParameters: null,
    drawdownStatus: null,
    dashboard: null,
    alerts: [],
    dailyPerformance: null,
    positionSize: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => { state.error = null; },
    addAlert: (state, action) => {
      state.alerts.unshift(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRiskParameters.fulfilled, (state, action) => {
        state.riskParameters = action.payload;
        state.loading = false;
      })
      .addCase(fetchRiskParameters.pending, (state) => { state.loading = true; })
      .addCase(fetchRiskParameters.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchDrawdownStatus.fulfilled, (state, action) => {
        state.drawdownStatus = action.payload;
        state.loading = false;
      })
      .addCase(fetchDrawdownStatus.pending, (state) => { state.loading = true; })
      .addCase(fetchDrawdownStatus.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchRiskDashboard.fulfilled, (state, action) => {
        state.dashboard = action.payload;
        state.loading = false;
      })
      .addCase(fetchRiskDashboard.pending, (state) => { state.loading = true; })
      .addCase(fetchRiskDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchRiskAlerts.fulfilled, (state, action) => {
        state.alerts = action.payload;
        state.loading = false;
      })
      .addCase(fetchRiskAlerts.pending, (state) => { state.loading = true; })
      .addCase(fetchRiskAlerts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchDailyPerformance.fulfilled, (state, action) => {
        state.dailyPerformance = action.payload;
      })
      .addCase(calculatePositionSize.fulfilled, (state, action) => {
        state.positionSize = action.payload;
      });
  },
});

export const { clearError, addAlert } = riskSlice.actions;
export default riskSlice.reducer;
