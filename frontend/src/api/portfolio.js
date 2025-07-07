import useSWR, { mutate } from 'swr';
import { useMemo } from 'react';
import { fetcher } from 'utils/axios';

const endpoints = {
  latest: '/portfolio/latest',
  history: '/portfolio/'
};

export function useGetLatestPortfolio() {
  const { data, isLoading, error, isValidating } = useSWR(
    endpoints.latest,
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
      portfolioValidating: isValidating,
      totalHeatIndex: data?.total_heat_index
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export function useGetPortfolioHistory() {
  const { data, isLoading, error, isValidating } = useSWR(
    endpoints.history,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  const memoized = useMemo(
    () => ({
      history: data,
      historyLoading: isLoading,
      historyError: error,
      historyValidating: isValidating,
      historyEmpty: !isLoading && (!data || data.length === 0)
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export function refreshLatestPortfolio() {
  return mutate(endpoints.latest);
}

export function refreshPortfolioHistory() {
  return mutate(endpoints.history);
}
