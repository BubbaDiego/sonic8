import axios from 'utils/axios';

const API_BASE = import.meta.env.VITE_APP_API_URL || 'http://localhost:5000';

export async function runSonicCycle() {
  try {
    return await axios.post('/monitors/sonic_cycle');
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export const runSonicMonitor = () =>
  axios.post('/monitors/sonic_monitor').then(r => r.data);

export const resetLiquidSnooze = () =>
  axios.post('/api/monitor-status/reset-liquid-snooze').then(r => r.data);

export function subscribeToSonicEvents(onMessage) {
  const es = new EventSource(`${API_BASE}/monitors/sonic_events`);
  es.addEventListener('sonic_complete', () => onMessage && onMessage());
  return es;
}

