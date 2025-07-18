import useSWR, { mutate } from 'swr';
import { useMemo } from 'react';
import axios, { fetcher } from 'utils/axios';

const endpoints = {
  active: '/session',
  history: '/session/history',
  start: '/session',
  reset: '/session/reset',
  close: '/session/close'
};

export function useGetActiveSession() {
  const { data, isLoading, error, isValidating } = useSWR(
    endpoints.active,
    fetcher,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false
    }
  );

  const memoized = useMemo(
    () => ({
      session: data,
      sessionLoading: isLoading,
      sessionError: error,
      sessionValidating: isValidating
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export function useGetSessionHistory() {
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
      sessions: data,
      sessionsLoading: isLoading,
      sessionsError: error,
      sessionsValidating: isValidating,
      sessionsEmpty: !isLoading && (!data || data.length === 0)
    }),
    [data, error, isLoading, isValidating]
  );

  return memoized;
}

export async function startSession(payload) {
  const res = await axios.post(endpoints.start, payload);
  return res.data;
}

export async function updateSession(patch) {
  const res = await axios.put(endpoints.active, patch);
  return res.data;
}

export async function resetSession() {
  const res = await axios.post(endpoints.reset);
  return res.data;
}

export async function closeSession() {
  const res = await axios.post(endpoints.close);
  return res.data;
}

export function refreshActiveSession() {
  return mutate(endpoints.active);
}

export function refreshSessionHistory() {
  return mutate(endpoints.history);
}

export default {
  useGetActiveSession,
  useGetSessionHistory,
  startSession,
  updateSession,
  resetSession,
  closeSession,
  refreshActiveSession,
  refreshSessionHistory,
  endpoints
};
