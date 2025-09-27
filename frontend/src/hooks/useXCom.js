import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from 'api/xcom';

// Providers hook
export const useProviders = () => {
  return useQuery({
    queryKey: ['xcom', 'providers'],
    queryFn: api.getProviders
  });
};

export const useProvidersResolved = () => {
  return useQuery({
    queryKey: ['xcom', 'providers_resolved'],
    queryFn: api.getProvidersResolved
  });
};

// Mutation hook to save providers
export const useSaveProviders = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.saveProviders,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['xcom', 'providers'] });
      queryClient.invalidateQueries({ queryKey: ['xcom', 'providers_resolved'] });
    }
  });
};

// Status hook
export const useStatus = () => {
  return useQuery({
    queryKey: ['xcom', 'status'],
    queryFn: api.getStatus,
    refetchInterval: 30000,
  });
};

// Test message mutation hook
export const useTestMessage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ mode, recipient, subject, body, level }) => api.testMessage(mode, recipient, subject, body, level),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['xcom', 'status'] })
  });
};

// Heartbeat mutation hook
export const useRunHeartbeat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.runHeartbeat,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['xcom', 'status'] })
  });
};
