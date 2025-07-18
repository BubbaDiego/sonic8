import axios from 'utils/axios';

const BASE = '/alert_thresholds';

export async function listThresholds() {
  const res = await axios.get(`${BASE}/`);
  return res.data;
}

export async function getThreshold(id) {
  const res = await axios.get(`${BASE}/${id}`);
  return res.data;
}

export async function createThreshold(payload) {
  const res = await axios.post(`${BASE}/`, payload);
  return res.data;
}

export async function updateThreshold(id, payload) {
  const res = await axios.put(`${BASE}/${id}`, payload);
  return res.data;
}

export async function deleteThreshold(id) {
  const res = await axios.delete(`${BASE}/${id}`);
  return res.data;
}

export default {
  listThresholds,
  getThreshold,
  createThreshold,
  updateThreshold,
  deleteThreshold,
};
