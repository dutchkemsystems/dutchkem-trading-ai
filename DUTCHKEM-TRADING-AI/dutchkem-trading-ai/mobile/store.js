import { configureStore } from '@reduxjs/toolkit';

// Simple reducer for mobile app
const authReducer = (state = { user: null, token: null }, action) => {
  switch (action.type) {
    case 'SET_CREDENTIALS':
      return { ...state, user: action.payload.user, token: action.payload.token };
    case 'LOGOUT':
      return { ...state, user: null, token: null };
    default:
      return state;
  }
};

const tradingReducer = (state = { positions: [], portfolio: null }, action) => {
  switch (action.type) {
    case 'SET_POSITIONS':
      return { ...state, positions: action.payload };
    case 'SET_PORTFOLIO':
      return { ...state, portfolio: action.payload };
    default:
      return state;
  }
};

export const store = configureStore({
  reducer: {
    auth: authReducer,
    trading: tradingReducer,
  },
});

export default store;
