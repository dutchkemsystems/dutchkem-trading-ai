import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchPerformance = createAsyncThunk(
  'analytics/fetchPerformance',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/analytics/performance/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch performance' });
    }
  }
);

export const fetchRiskAnalytics = createAsyncThunk(
  'analytics/fetchRisk',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/analytics/risk/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch risk analytics' });
    }
  }
);

export const fetchSignalAnalytics = createAsyncThunk(
  'analytics/fetchSignals',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/analytics/signals/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch signal analytics' });
    }
  }
);

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState: {
    performance: null,
    riskAnalytics: null,
    signalAnalytics: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPerformance.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPerformance.fulfilled, (state, action) => {
        state.loading = false;
        state.performance = action.payload;
      })
      .addCase(fetchPerformance.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchRiskAnalytics.fulfilled, (state, action) => {
        state.riskAnalytics = action.payload;
      })
      .addCase(fetchSignalAnalytics.fulfilled, (state, action) => {
        state.signalAnalytics = action.payload;
      });
  },
});

export const { clearError } = analyticsSlice.actions;
export default analyticsSlice.reducer;
