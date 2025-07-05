import axios from 'utils/axios';

const endpoints = {
  list: '/alert_thresholds/',
  bulk: '/alert_thresholds/bulk'
};

export async function getAllThresholds() {
  const res = await axios.get(endpoints.list);
  return res.data;
}

export async function saveAllThresholds(config) {
  const res = await axios.put(endpoints.bulk, config);
  return res.data;
}
