import useSWR, { mutate } from 'swr';
import { useMemo } from 'react';
import { fetcher } from 'utils/axios';

const endpoints = {
  summary: '/monitor_status/'
};

export function useGetMonitorStatus() {
  const { data, isLoading, error, isValidating } = useSWR(
    endpoints.summary,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  const memoized = useMemo(
    () => ({
      monitorStatus: data,
      monitorStatusLoading: isLoading,
      monitorStatusError: error,
      monitorStatusValidating: isValidating
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export function refreshMonitorStatus() {
  return mutate(endpoints.summary);
}

export { endpoints };
