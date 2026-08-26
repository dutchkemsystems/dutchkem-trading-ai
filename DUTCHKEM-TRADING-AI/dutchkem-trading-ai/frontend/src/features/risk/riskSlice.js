import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  riskParameters: null,
  drawdownStatus: null,
  dailyPerformance: null,
  alerts: [],
  loading: false,
  error: null,
};

const riskSlice = createSlice({
  name: 'risk',
  initialState,
  reducers: {
    setRiskParameters: (state, action) => {
      state.riskParameters = action.payload;
    },
    setDrawdownStatus: (state, action) => {
      state.drawdownStatus = action.payload;
    },
    setDailyPerformance: (state, action) => {
      state.dailyPerformance = action.payload;
    },
    setAlerts: (state, action) => {
      state.alerts = action.payload;
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
  setRiskParameters, setDrawdownStatus, setDailyPerformance,
  setAlerts, setLoading, setError
} = riskSlice.actions;
export default riskSlice.reducer;
