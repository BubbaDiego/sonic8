// src/api/jupiter.js
import client from 'lib/api/sonicClient';

export async function createSpotTrigger(payload) {
  const { data } = await client.post('/api/jupiter/trigger/create', payload);
  return data;
}

export async function listSpotTriggers(params = {}) {
  const { data } = await client.get('/api/jupiter/trigger/orders', { params });
  return data;
}

export async function cancelSpotTrigger(payload) {
  const { data } = await client.post('/api/jupiter/trigger/cancel', payload);
  return data;
}

export async function swapQuote(payload) {
  const { data } = await client.post('/api/jupiter/swap/quote', payload);
  return data;
}

export async function swapExecute(payload) {
  const { data } = await client.post('/api/jupiter/swap/execute', payload);
  return data;
}

// Perps (skeleton)
export async function attachPerpTrigger(payload) {
  const { data } = await client.post('/api/jupiter/perps/attach-trigger', payload);
  return data;
}

export async function listPerpPositions() {
  const { data } = await client.get('/api/jupiter/perps/positions');
  return data;
}
