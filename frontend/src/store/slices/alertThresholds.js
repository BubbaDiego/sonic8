import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'utils/axios';

const initialState = {
  data: {},
  loading: false,
  error: null
};

export const fetchThresholds = createAsyncThunk(
  'thresholds/fetch',
  async () => {
    const response = await axios.get('/alert_thresholds/bulk');
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

const alertThresholds = createSlice({

  name: 'thresholds',
  initialState,
  reducers: {
    setThresholds(state, action) {
      state.data = action.payload;
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
        state.data = action.payload;
      })
      .addCase(fetchThresholds.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(persistThresholds.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(persistThresholds.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(persistThresholds.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  }
});

export const { setThresholds } = alertThresholds.actions;

export default alertThresholds.reducer;
