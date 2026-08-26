import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  positions: [],
  orders: [],
  trades: [],
  symbols: [],
  portfolio: null,
  loading: false,
  error: null,
};

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    setPositions: (state, action) => {
      state.positions = action.payload;
    },
    setOrders: (state, action) => {
      state.orders = action.payload;
    },
    setTrades: (state, action) => {
      state.trades = action.payload;
    },
    setSymbols: (state, action) => {
      state.symbols = action.payload;
    },
    setPortfolio: (state, action) => {
      state.portfolio = action.payload;
    },
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
  },
});

export const {
  setPositions, setOrders, setTrades, setSymbols,
  setPortfolio, setLoading, setError
} = tradingSlice.actions;
export default tradingSlice.reducer;
