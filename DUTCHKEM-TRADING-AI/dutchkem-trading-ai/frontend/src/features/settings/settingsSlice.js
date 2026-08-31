import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchUserProfile = createAsyncThunk(
  'settings/fetchProfile',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/accounts/profile/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch profile' });
    }
  }
);

export const updateProfile = createAsyncThunk(
  'settings/updateProfile',
  async (profileData, { rejectWithValue }) => {
    try {
      const response = await api.patch('/accounts/profile/', profileData);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to update profile' });
    }
  }
);

export const changePassword = createAsyncThunk(
  'settings/changePassword',
  async (passwordData, { rejectWithValue }) => {
    try {
      const response = await api.post('/accounts/change-password/', passwordData);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to change password' });
    }
  }
);

export const enableMFA = createAsyncThunk(
  'settings/enableMFA',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.post('/accounts/mfa/enable/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to enable MFA' });
    }
  }
);

export const fetchKYCStatus = createAsyncThunk(
  'settings/fetchKYC',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/payments/kyc/status/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: 'Failed to fetch KYC status' });
    }
  }
);

const settingsSlice = createSlice({
  name: 'settings',
  initialState: {
    profile: null,
    kycStatus: null,
    mfaEnabled: false,
    loading: false,
    error: null,
    success: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearSuccess: (state) => {
      state.success = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUserProfile.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUserProfile.fulfilled, (state, action) => {
        state.loading = false;
        state.profile = action.payload;
        state.mfaEnabled = action.payload.mfa_enabled;
      })
      .addCase(fetchUserProfile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(updateProfile.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.loading = false;
        state.profile = action.payload;
        state.success = 'Profile updated successfully';
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(changePassword.fulfilled, (state) => {
        state.success = 'Password changed successfully';
      })
      .addCase(enableMFA.fulfilled, (state, action) => {
        state.mfaEnabled = true;
        state.profile = { ...state.profile, mfa_enabled: true };
        state.success = 'MFA enabled successfully';
      })
      .addCase(fetchKYCStatus.fulfilled, (state, action) => {
        state.kycStatus = action.payload;
      });
  },
});

export const { clearError, clearSuccess } = settingsSlice.actions;
export default settingsSlice.reducer;
