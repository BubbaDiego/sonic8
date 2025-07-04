import useSWR, { mutate } from 'swr';
import { useMemo } from 'react';
import { fetcher } from 'utils/axios';

const endpoints = {
  list: '/positions/'
};

export function useGetPositions(enabled = true) {
  const { data, isLoading, error, isValidating } = useSWR(
    enabled ? endpoints.list : null,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  const memoized = useMemo(
    () => ({
      positions: data,
      positionsLoading: isLoading,
      positionsError: error,
      positionsValidating: isValidating,
      positionsEmpty: !isLoading && (!data || data.length === 0)
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export function refreshPositions() {
  return mutate(endpoints.list);
}
