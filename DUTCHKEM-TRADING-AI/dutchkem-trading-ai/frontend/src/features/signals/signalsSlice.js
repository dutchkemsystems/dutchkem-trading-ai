import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  signals: [],
  confluenceScores: [],
  activeSignals: [],
  loading: false,
  error: null,
};

const signalsSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    setSignals: (state, action) => {
      state.signals = action.payload;
    },
    setConfluenceScores: (state, action) => {
      state.confluenceScores = action.payload;
    },
    setActiveSignals: (state, action) => {
      state.activeSignals = action.payload;
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
  setSignals, setConfluenceScores, setActiveSignals,
  setLoading, setError
} = signalsSlice.actions;
export default signalsSlice.reducer;
