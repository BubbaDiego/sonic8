export interface PositionDB {
  id: string;
  asset_type: string;
  position_type: 'LONG' | 'SHORT';
  entry_price: number;
  liquidation_price: number;
  travel_percent: number;
  value: number;
  collateral: number;
  size: number;
  leverage: number;
  wallet_name: string;
  current_price: number;
  liquidation_distance: number;
  heat_index: number;
  hedge_buddy_id?: string;
  status: string;
  stale: number;
  last_updated: string;
}
