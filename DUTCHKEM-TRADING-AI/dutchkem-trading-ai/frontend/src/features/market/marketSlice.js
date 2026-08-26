import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  livePrices: {},
  marketData: [],
  economicCalendar: [],
  sentiment: [],
  loading: false,
  error: null,
};

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    setLivePrices: (state, action) => {
      state.livePrices = { ...state.livePrices, ...action.payload };
    },
    setMarketData: (state, action) => {
      state.marketData = action.payload;
    },
    setEconomicCalendar: (state, action) => {
      state.economicCalendar = action.payload;
    },
    setSentiment: (state, action) => {
      state.sentiment = action.payload;
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
  setLivePrices, setMarketData, setEconomicCalendar,
  setSentiment, setLoading, setError
} = marketSlice.actions;
export default marketSlice.reducer;
