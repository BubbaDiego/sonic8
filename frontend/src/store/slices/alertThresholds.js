import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'utils/axios';

export const fetchThresholds = createAsyncThunk('alertThresholds/fetch', async () => {
  const res = await axios.get('/alert_thresholds/bulk');
  return res.data;
});

export const persistThresholds = createAsyncThunk(
  'alertThresholds/persist',
  async (_, { getState }) => {
    const { thresholds, cooldowns } = getState().alertThresholds;
    const res = await axios.put('/alert_thresholds/bulk', { thresholds, cooldowns });
    return res.data;
  }
);

const alertThresholds = createSlice({
  name: 'alertThresholds',
  initialState: { thresholds: [], cooldowns: {} },
  reducers: {
    setThreshold(state, action) {
      const { id, field, value } = action.payload;
      const t = state.thresholds.find((th) => th.id === id);
      if (t) t[field] = value;
    },
    setCooldown(state, action) {
      const { field, value } = action.payload;
      state.cooldowns[field] = value;
    },
    setAll(state, action) {
      state.thresholds = action.payload.thresholds || [];
      state.cooldowns = action.payload.cooldowns || {};
    }
  },
  extraReducers: (builder) => {
    builder.addCase(fetchThresholds.fulfilled, (state, action) => {
      state.thresholds = action.payload.thresholds || [];
      state.cooldowns = action.payload.cooldowns || {};
    });
  }
});

export const { setThreshold, setCooldown, setAll } = alertThresholds.actions;
export default alertThresholds.reducer;
