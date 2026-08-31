import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { signalsAPI } from '../../services/api';

export const fetchSignals = createAsyncThunk(
  'signals/fetchSignals',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await signalsAPI.getSignals(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch signals');
    }
  }
);

export const fetchActiveSignals = createAsyncThunk(
  'signals/fetchActive',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await signalsAPI.getActiveSignals();
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch active signals');
    }
  }
);

export const fetchConfluenceScores = createAsyncThunk(
  'signals/fetchConfluence',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await signalsAPI.getConfluenceScores(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch confluence scores');
    }
  }
);

export const generateSignal = createAsyncThunk(
  'signals/generate',
  async (signalData, { rejectWithValue }) => {
    try {
      const { data } = await signalsAPI.generateSignal(signalData);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to generate signal');
    }
  }
);

const signalsSlice = createSlice({
  name: 'signals',
  initialState: {
    signals: [],
    activeSignals: [],
    confluenceScores: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => { state.error = null; },
    updateSignal: (state, action) => {
      const idx = state.signals.findIndex((s) => s.id === action.payload.id);
      if (idx !== -1) state.signals[idx] = action.payload;
      const activeIdx = state.activeSignals.findIndex((s) => s.id === action.payload.id);
      if (activeIdx !== -1) state.activeSignals[activeIdx] = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSignals.pending, (state) => { state.loading = true; })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.signals = action.payload;
        state.loading = false;
      })
      .addCase(fetchSignals.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchActiveSignals.fulfilled, (state, action) => {
        state.activeSignals = action.payload;
        state.loading = false;
      })
      .addCase(fetchActiveSignals.pending, (state) => { state.loading = true; })
      .addCase(fetchActiveSignals.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchConfluenceScores.fulfilled, (state, action) => {
        state.confluenceScores = action.payload;
        state.loading = false;
      })
      .addCase(fetchConfluenceScores.pending, (state) => { state.loading = true; })
      .addCase(fetchConfluenceScores.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(generateSignal.fulfilled, (state, action) => {
        state.signals.unshift(action.payload);
      });
  },
});

export const { clearError, updateSignal } = signalsSlice.actions;
export default signalsSlice.reducer;
