import axios from 'utils/axios';

export function runFullCycle() {
  return axios.post('/cyclone/run');
}

export function runPriceUpdate() {
  return axios.post('/cyclone/prices');
}

export function runPositionUpdate() {
  return axios.post('/cyclone/positions');
}

export function deleteAllData() {
  return axios.delete('/cyclone/data');
}
