import axios from 'utils/axios';

export function patchLiquidationSettings(patch) {
  // patch = { thresholds?: {...}, blast_radius?: {...}, notifications?: {...}, snooze_seconds?: number }
  return axios.post('/api/monitor-settings/liquidation', patch).then((r) => r.data);
}
