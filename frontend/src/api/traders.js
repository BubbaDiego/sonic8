// traders.js
import axios from 'utils/axios';

export const getTraders = async () => {
  const response = await axios.get('/api/traders');
  return response.data;
};

export const getTrader = async (name) => {
  const response = await axios.get(`/api/traders/${name}`);
  return response.data;
};

export const createTrader = async (traderData) => {
  const response = await axios.post('/api/traders', traderData);
  return response.data;
};

export const updateTrader = async (name, traderData) => {
  const response = await axios.put(`/api/traders/${name}`, traderData);
  return response.data;
};

export const deleteTrader = async (name) => {
  const response = await axios.delete(`/api/traders/${name}`);
  return response.data;
};
