import useSWR from 'swr';
import { useMemo } from 'react';
import { fetcher } from 'utils/axios';

const endpoints = {
  list: '/positions/'
};

export function useGetPositions() {
  const { data, isLoading, error, isValidating } = useSWR(endpoints.list, fetcher, {
    revalidateIfStale: false,
    revalidateOnFocus: false,
    revalidateOnReconnect: false
  });

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
