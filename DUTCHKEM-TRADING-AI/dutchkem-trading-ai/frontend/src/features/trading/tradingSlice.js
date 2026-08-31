import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { tradingAPI } from '../../services/api';

export const fetchSymbols = createAsyncThunk(
  'trading/fetchSymbols',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.getSymbols();
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch symbols');
    }
  }
);

export const fetchTrades = createAsyncThunk(
  'trading/fetchTrades',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.getTrades(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch trades');
    }
  }
);

export const createTrade = createAsyncThunk(
  'trading/createTrade',
  async (tradeData, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.createTrade(tradeData);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to create trade');
    }
  }
);

export const closeTrade = createAsyncThunk(
  'trading/closeTrade',
  async (tradeId, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.closeTrade(tradeId);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to close trade');
    }
  }
);

export const fetchOrders = createAsyncThunk(
  'trading/fetchOrders',
  async (params, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.getOrders(params);
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch orders');
    }
  }
);

export const createOrder = createAsyncThunk(
  'trading/createOrder',
  async (orderData, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.createOrder(orderData);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to create order');
    }
  }
);

export const cancelOrder = createAsyncThunk(
  'trading/cancelOrder',
  async (orderId, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.cancelOrder(orderId);
      return { orderId, ...data };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to cancel order');
    }
  }
);

export const fetchPositions = createAsyncThunk(
  'trading/fetchPositions',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.getPositions();
      return data.results || data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch positions');
    }
  }
);

export const fetchPortfolio = createAsyncThunk(
  'trading/fetchPortfolio',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await tradingAPI.getPortfolio();
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch portfolio');
    }
  }
);

const tradingSlice = createSlice({
  name: 'trading',
  initialState: {
    positions: [],
    orders: [],
    trades: [],
    symbols: [],
    portfolio: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => { state.error = null; },
    updatePosition: (state, action) => {
      const idx = state.positions.findIndex((p) => p.id === action.payload.id);
      if (idx !== -1) state.positions[idx] = action.payload;
    },
    removeOrder: (state, action) => {
      state.orders = state.orders.filter((o) => o.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSymbols.pending, (state) => { state.loading = true; })
      .addCase(fetchSymbols.fulfilled, (state, action) => {
        state.symbols = action.payload;
        state.loading = false;
      })
      .addCase(fetchSymbols.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchTrades.fulfilled, (state, action) => {
        state.trades = action.payload;
        state.loading = false;
      })
      .addCase(fetchTrades.pending, (state) => { state.loading = true; })
      .addCase(fetchTrades.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createTrade.fulfilled, (state, action) => {
        state.trades.unshift(action.payload);
      })
      .addCase(closeTrade.fulfilled, (state, action) => {
        const idx = state.trades.findIndex((t) => t.id === action.payload.id);
        if (idx !== -1) state.trades[idx] = action.payload;
      })
      .addCase(fetchOrders.fulfilled, (state, action) => {
        state.orders = action.payload;
        state.loading = false;
      })
      .addCase(fetchOrders.pending, (state) => { state.loading = true; })
      .addCase(fetchOrders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createOrder.fulfilled, (state, action) => {
        state.orders.unshift(action.payload);
      })
      .addCase(cancelOrder.fulfilled, (state, action) => {
        state.orders = state.orders.filter((o) => o.id !== action.payload.orderId);
      })
      .addCase(fetchPositions.fulfilled, (state, action) => {
        state.positions = action.payload;
        state.loading = false;
      })
      .addCase(fetchPositions.pending, (state) => { state.loading = true; })
      .addCase(fetchPositions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchPortfolio.fulfilled, (state, action) => {
        state.portfolio = action.payload;
        state.loading = false;
      });
  },
});

export const { clearError, updatePosition, removeOrder } = tradingSlice.actions;
export default tradingSlice.reducer;
