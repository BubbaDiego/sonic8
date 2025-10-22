import axios from 'utils/axios';
import useSWR from 'swr';

const fetcher = (u) => axios.get(u).then((r) => r.data);

export function useLiquidationSettings() {
  const { data, error, isLoading, mutate } = useSWR('/api/monitor-settings/liquidation', fetcher, {
    revalidateIfStale: false,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  return {
    data,
    thresholds: data?.thresholds ?? {},
    blastRadius: data?.blast_radius ?? {},
    snoozeSeconds: typeof data?.snooze_seconds === 'number' ? data.snooze_seconds : 0,
    loading: isLoading,
    error,
    refresh: mutate,
  };
}

export const patchLiquidationSettings = (patch) =>
  axios.post('/api/monitor-settings/liquidation', patch).then((r) => r.data);
