import useSWR, { mutate } from 'swr';
import axios, { fetcher } from 'utils/axios';

const endpoints = {
  bulk: '/alert_thresholds/bulk'
};

export function useGetAlertThresholds(enabled = true) {
  const { data, isLoading, error, isValidating } = useSWR(
    enabled ? endpoints.bulk : null,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  return {
    thresholds: data?.thresholds || [],
    cooldowns: data?.cooldowns || {},
    loading: isLoading,
    error,
    isValidating
  };
}

export async function putAlertThresholds(config) {
  await axios.put(endpoints.bulk, config);
  mutate(endpoints.bulk);
}
