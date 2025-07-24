import axios from 'utils/axios';

export const runSonicMonitor = () =>
  axios.post('/monitors/sonic_monitor').then(r => r.data);
