
import axios from 'utils/axios';

// ---- CRUD for provider config ----
export const getProviders = () => axios.get('/xcom/providers').then(r => r.data);
export const saveProviders = (payload) => axios.put('/xcom/providers', payload).then(r => r.data);
export const getProvidersResolved = () => axios.get('/xcom/providers/resolved').then(r => r.data);

// ---- Status & heartbeat ----
export const getStatus = () => axios.get('/xcom/status').then(r => r.data);
export const runHeartbeat = () => axios.post('/monitors/xcom_monitor').then(r => r.data);
export const resetCooldown = () => axios.post('/xcom/cooldown/reset').then(r => r.data);
export const setCooldown = (seconds) =>
  axios.put('/xcom/cooldown', null, { params: { seconds } }).then(r => r.data);

// ---- Test message ----
export const testMessage = (mode, recipient, subject, body, level='LOW') =>
  axios.post('/xcom/test', { mode, recipient, subject, body, level }).then(r => r.data);
