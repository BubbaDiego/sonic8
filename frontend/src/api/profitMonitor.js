import axios from 'utils/axios';

export const getProfitCfg = async () => (await axios.get('/api/monitor-settings/profit')).data;
export const saveProfitCfg = async (payload) => (await axios.post('/api/monitor-settings/profit', payload)).data;

export default {
  getProfitCfg,
  saveProfitCfg
};
