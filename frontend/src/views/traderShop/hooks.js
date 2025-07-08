// src/views/traderShop/hooks.js
// Thin wrappers around existing API helpers so the view remains decoupled.
import useSWR, { mutate } from 'swr';
import axios from 'utils/axios';

const endpoints = {
  traders: '/api/traders', // <- Fixed here!
  quickImport: '/api/traders/quick_import',
  starWarsWallets: '/api/wallets/star_wars',
  export: '/api/traders/export'
};

const fetcher = (url) => axios.get(url).then((res) => res.data);

// --- Traders ---
export function useTraders() {
  const { data, error, isLoading } = useSWR(endpoints.traders, fetcher);
  return {
    traders: data || [],
    isLoading,
    isError: !!error,
    refresh: () => mutate(endpoints.traders)
  };
}

export async function createTrader(payload) {
  await axios.post(endpoints.traders, payload);
  mutate(endpoints.traders);
}

export async function updateTrader(name, payload) {
  await axios.put(`${endpoints.traders}/${encodeURIComponent(name)}`, payload);
  mutate(endpoints.traders);
}

export async function deleteTrader(name) {
  await axios.delete(`${endpoints.traders}/${encodeURIComponent(name)}`);
  mutate(endpoints.traders);
}

// --- Quick‑import Star Wars traders ---
export async function importStarWarsTraders() {
  await axios.post(endpoints.starWarsWallets).catch(() => {});
  await axios.post(endpoints.quickImport);
  mutate(endpoints.traders);
}

// --- Export ---
export async function exportTraders() {
  const { data } = await axios.get(endpoints.export, { responseType: 'blob' });
  const blob = new Blob([data], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'active_traders.json';
  a.click();
  window.URL.revokeObjectURL(url);
}
