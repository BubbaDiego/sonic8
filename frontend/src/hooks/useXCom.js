
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from 'api/xcom';

export const useProviders = () => {
  const qc = useQueryClient();
  return {
    ...useQuery(['xcom','providers'], api.getProviders),
    saveProviders: useMutation(api.saveProviders, {
      onSuccess: () => qc.invalidateQueries(['xcom','providers'])
    })
  };
};

export const useStatus = () => {
  const qc = useQueryClient();
  return {
    ...useQuery(['xcom','status'], api.getStatus, { refetchInterval: 30000 }),
    refetchStatus: () => qc.invalidateQueries(['xcom','status']),
    runHeartbeat: useMutation(api.runHeartbeat, {
      onSuccess: () => qc.invalidateQueries(['xcom','status'])
    })
  };
};

export const useTestMessage = () => {
  return useMutation(api.testMessage);
};
