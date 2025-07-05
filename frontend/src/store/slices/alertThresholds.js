import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'utils/axios';
import { createThreshold as apiCreateThreshold } from 'api/alertThresholds';

const initialState = {
  rows: [],
  loading: false,
  error: null
};

export const fetchThresholds = createAsyncThunk(
  'thresholds/fetch',
  async () => {
    const response = await axios.get('/alert_thresholds/');
    return response.data;
  }
);

export const persistThresholds = createAsyncThunk(
  'thresholds/persist',
  async (config) => {
    await axios.put('/alert_thresholds/bulk', config);
    return config;
  }
);

export const createThreshold = createAsyncThunk(
  'thresholds/create',
  async (payload) => {
    const res = await apiCreateThreshold(payload);
    return res;
  }
);

const alertThresholds = createSlice({

  name: 'thresholds',
  initialState,
  reducers: {
    setThresholds(state, action) {
      state.rows = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchThresholds.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchThresholds.fulfilled, (state, action) => {
        state.loading = false;
        state.rows = action.payload;
      })
      .addCase(fetchThresholds.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(persistThresholds.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(persistThresholds.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(persistThresholds.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(createThreshold.fulfilled, (state, action) => {
        state.rows.push(action.payload);
      });
  }
});

export const { setThresholds } = alertThresholds.actions;

export default alertThresholds.reducer;
