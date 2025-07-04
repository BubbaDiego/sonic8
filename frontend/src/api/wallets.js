import useSWR from 'swr';
import { useMemo } from 'react';
import axios, { fetcher } from 'utils/axios';
import { mutate } from 'swr';

const endpoints = {
  list: '/wallets/'
};

export function useGetWallets(enabled = true) {
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
      wallets: data,
      walletsLoading: isLoading,
      walletsError: error,
      walletsValidating: isValidating,
      walletsEmpty: !isLoading && (!data || data.length === 0)
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export async function createWallet(wallet) {
  const res = await axios.post(endpoints.list, wallet);
  return res.data;
}

export async function updateWallet(name, wallet) {
  const res = await axios.put(`${endpoints.list}${encodeURIComponent(name)}`, wallet);
  return res.data;
}

export async function deleteWallet(name) {
  const res = await axios.delete(`${endpoints.list}${encodeURIComponent(name)}`);
  return res.data;
}

export function refreshWallets() {
  return mutate(endpoints.list);
}
