import { useQuery } from '@tanstack/react-query';
import { PositionDB } from '../types/position';

export function usePositions() {
  return useQuery<PositionDB[]>({
    queryKey: ['positions'],
    queryFn: () => fetch('/positions/').then(r => r.json())
  });
}

export interface HedgeSummary {
  id: string;
  asset_image: string;
  wallet_image: string;
  total_value: number;
  long_size_ratio: number;
  short_size_ratio: number;
  long_leverage: number;
  short_leverage: number;
  total_heat_index: number;
}

export function useHedges() {
  return useQuery<HedgeSummary[]>({
    queryKey: ['hedges'],
    queryFn: () =>
      fetch('/sonic_labs/api/hedges')
        .then(r => r.json())
        .then(d => d.hedges ?? [])
  });
}

export function useHedgePositions(hedgeId: string | null) {
  return useQuery<PositionDB[]>({
    enabled: !!hedgeId,
    queryKey: ['hedgePositions', hedgeId],
    queryFn: () =>
      fetch(`/sonic_labs/api/hedge_positions?hedge_id=${hedgeId}`)
        .then(r => r.json())
        .then(d => d.positions ?? [])
  });
}

export interface HedgeEvalRow {
  position_type: 'long' | 'short';
  value: number;
  travel_percent: number;
  liquidation_distance: number;
  heat_index: number;
}

export interface HedgeEvalPayload {
  long?: HedgeEvalRow;
  short?: HedgeEvalRow;
  totals?: {
    total_value: number;
    avg_travel_percent: number;
    avg_heat_index: number;
  };
}

export function useHedgeEvaluation(hedgeId: string | null, price: number) {
  return useQuery<HedgeEvalPayload>({
    enabled: !!hedgeId,
    queryKey: ['hedgeEval', hedgeId, price],
    queryFn: () =>
      fetch(`/sonic_labs/api/evaluate_hedge?hedge_id=${hedgeId}&price=${price}`)
        .then(r => r.json())
  });
}
