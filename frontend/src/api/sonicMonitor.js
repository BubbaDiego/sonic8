import axios from 'utils/axios';

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

