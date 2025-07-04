import useSWR from 'swr';
import { useMemo } from 'react';
import { fetcher } from 'utils/axios';

const endpoints = {
  key: 'api/portfolio',
  latest: '/portfolio/latest'
};

export function useGetLatestPortfolio() {
  const { data, isLoading, error, isValidating } = useSWR(
    endpoints.key + endpoints.latest,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  const memoized = useMemo(
    () => ({
      portfolio: data,
      portfolioLoading: isLoading,
      portfolioError: error,
      portfolioValidating: isValidating
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}
