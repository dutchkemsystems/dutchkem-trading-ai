import { configureStore } from '@reduxjs/toolkit';
import authReducer from './features/auth/authSlice';
import tradingReducer from './features/trading/tradingSlice';
import signalsReducer from './features/signals/signalsSlice';
import riskReducer from './features/risk/riskSlice';
import marketReducer from './features/market/marketSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    trading: tradingReducer,
    signals: signalsReducer,
    risk: riskReducer,
    market: marketReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
