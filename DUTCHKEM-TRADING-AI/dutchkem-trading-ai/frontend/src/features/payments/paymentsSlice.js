import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchTransactions = createAsyncThunk(
  'payments/fetchTransactions',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await api.get('/payments/transactions/', { params });
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch transactions' });
    }
  }
);

export const initializeDeposit = createAsyncThunk(
  'payments/initializeDeposit',
  async (depositData, { rejectWithValue }) => {
    try {
      const response = await api.post('/payments/deposit/', depositData);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Deposit initialization failed' });
    }
  }
);

export const verifyDeposit = createAsyncThunk(
  'payments/verifyDeposit',
  async (reference, { rejectWithValue }) => {
    try {
      const response = await api.post('/payments/verify/', { reference });
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Verification failed' });
    }
  }
);

export const createWithdrawal = createAsyncThunk(
  'payments/createWithdrawal',
  async (withdrawalData, { rejectWithValue }) => {
    try {
      const response = await api.post('/payments/withdrawal/', withdrawalData);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Withdrawal failed' });
    }
  }
);

export const fetchPaymentGateways = createAsyncThunk(
  'payments/fetchGateways',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/payments/gateways/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch gateways' });
    }
  }
);

const paymentsSlice = createSlice({
  name: 'payments',
  initialState: {
    transactions: [],
    gateways: [],
    depositResult: null,
    withdrawalResult: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearDepositResult: (state) => {
      state.depositResult = null;
    },
    clearWithdrawalResult: (state) => {
      state.withdrawalResult = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTransactions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTransactions.fulfilled, (state, action) => {
        state.loading = false;
        state.transactions = action.payload.results || action.payload;
      })
      .addCase(fetchTransactions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(initializeDeposit.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(initializeDeposit.fulfilled, (state, action) => {
        state.loading = false;
        state.depositResult = action.payload;
      })
      .addCase(initializeDeposit.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createWithdrawal.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createWithdrawal.fulfilled, (state, action) => {
        state.loading = false;
        state.withdrawalResult = action.payload;
      })
      .addCase(createWithdrawal.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchPaymentGateways.fulfilled, (state, action) => {
        state.gateways = action.payload.results || action.payload;
      });
  },
});

export const { clearError, clearDepositResult, clearWithdrawalResult } = paymentsSlice.actions;
export default paymentsSlice.reducer;
