import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchExpertAdvisors = createAsyncThunk(
  'eas/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/eas/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch EAs' });
    }
  }
);

export const createExpertAdvisor = createAsyncThunk(
  'eas/create',
  async (eaData, { rejectWithValue }) => {
    try {
      const response = await api.post('/eas/', eaData);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to create EA' });
    }
  }
);

export const deployExpertAdvisor = createAsyncThunk(
  'eas/deploy',
  async (eaId, { rejectWithValue }) => {
    try {
      const response = await api.post(`/eas/${eaId}/deploy/`);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Deployment failed' });
    }
  }
);

export const fetchBacktestResults = createAsyncThunk(
  'eas/fetchBacktests',
  async (eaId, { rejectWithValue }) => {
    try {
      const response = await api.get(`/eas/${eaId}/backtests/`);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch backtests' });
    }
  }
);

const easSlice = createSlice({
  name: 'eas',
  initialState: {
    expertAdvisors: [],
    backtestResults: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchExpertAdvisors.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchExpertAdvisors.fulfilled, (state, action) => {
        state.loading = false;
        state.expertAdvisors = action.payload.results || action.payload;
      })
      .addCase(fetchExpertAdvisors.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createExpertAdvisor.fulfilled, (state, action) => {
        state.expertAdvisors.unshift(action.payload);
      })
      .addCase(deployExpertAdvisor.fulfilled, (state, action) => {
        const index = state.expertAdvisors.findIndex(ea => ea.id === action.payload.id);
        if (index !== -1) {
          state.expertAdvisors[index] = action.payload;
        }
      })
      .addCase(fetchBacktestResults.fulfilled, (state, action) => {
        state.backtestResults = action.payload.results || action.payload;
      });
  },
});

export const { clearError } = easSlice.actions;
export default easSlice.reducer;
