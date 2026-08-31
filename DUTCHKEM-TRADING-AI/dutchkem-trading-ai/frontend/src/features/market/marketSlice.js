import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { marketAPI } from '../../services/api';

export const fetchLivePrices = createAsyncThunk(
  'market/fetchLivePrices',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await marketAPI.getLivePrices();
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch live prices');
    }
  }
);

export const fetchMarketOverview = createAsyncThunk(
  'market/fetchOverview',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await marketAPI.getOverview();
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch market overview');
    }
  }
);

export const fetchEconomicCalendar = createAsyncThunk(
  'market/fetchCalendar',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await marketAPI.getEconomicCalendar(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch economic calendar');
    }
  }
);

export const fetchSentiment = createAsyncThunk(
  'market/fetchSentiment',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await marketAPI.getSentiment(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch sentiment');
    }
  }
);

const marketSlice = createSlice({
  name: 'market',
  initialState: {
    livePrices: {},
    marketData: [],
    overview: null,
    economicCalendar: [],
    sentiment: [],
    loading: false,
    error: null,
  },
  reducers: {
    updateLivePrice: (state, action) => {
      const { symbol, price, change, changePercent, bid, ask } = action.payload;
      state.livePrices[symbol] = { price, change, changePercent, bid, ask, timestamp: Date.now() };
    },
    clearError: (state) => { state.error = null; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchLivePrices.pending, (state) => { state.loading = true; })
      .addCase(fetchLivePrices.fulfilled, (state, action) => {
        const pricesMap = {};
        (action.payload || []).forEach((p) => {
          pricesMap[p.symbol?.name || p.symbol] = {
            price: p.bid ? ((parseFloat(p.bid) + parseFloat(p.ask)) / 2).toFixed(5) : p.price,
            bid: p.bid,
            ask: p.ask,
            change: p.change,
            changePercent: p.change_percent,
            timestamp: Date.now(),
          };
        });
        state.livePrices = pricesMap;
        state.loading = false;
      })
      .addCase(fetchLivePrices.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchMarketOverview.fulfilled, (state, action) => {
        state.overview = action.payload;
        state.loading = false;
      })
      .addCase(fetchMarketOverview.pending, (state) => { state.loading = true; })
      .addCase(fetchEconomicCalendar.fulfilled, (state, action) => {
        state.economicCalendar = action.payload;
      })
      .addCase(fetchSentiment.fulfilled, (state, action) => {
        state.sentiment = action.payload;
      });
  },
});

export const { updateLivePrice, clearError } = marketSlice.actions;
export default marketSlice.reducer;
