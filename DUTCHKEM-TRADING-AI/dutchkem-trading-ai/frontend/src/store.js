import { configureStore } from '@reduxjs/toolkit';
import authReducer from './features/auth/authSlice';
import tradingReducer from './features/trading/tradingSlice';
import signalsReducer from './features/signals/signalsSlice';
import riskReducer from './features/risk/riskSlice';
import marketReducer from './features/market/marketSlice';
import paymentsReducer from './features/payments/paymentsSlice';
import easReducer from './features/eas/easSlice';
import analyticsReducer from './features/analytics/analyticsSlice';
import notificationsReducer from './features/notifications/notificationsSlice';
import settingsReducer from './features/settings/settingsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    trading: tradingReducer,
    signals: signalsReducer,
    risk: riskReducer,
    market: marketReducer,
    payments: paymentsReducer,
    eas: easReducer,
    analytics: analyticsReducer,
    notifications: notificationsReducer,
    settings: settingsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
