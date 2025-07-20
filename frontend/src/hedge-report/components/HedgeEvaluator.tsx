import { useState, useEffect } from 'react';
import {
  useHedges,
  useHedgePositions,
  useHedgeEvaluation
} from '../api/hooks';

export function HedgeEvaluator() {
  const { data: hedges = [] } = useHedges();
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!selected && hedges.length) setSelected(String(hedges[0].id));
  }, [hedges, selected]);

  const { data: positions = [] } = useHedgePositions(selected);

  const long = positions.find(p => p.position_type === 'LONG');
  const short = positions.find(p => p.position_type === 'SHORT');

  const current =
    long && short
      ? (long.current_price + short.current_price) / 2
      : long?.current_price ?? short?.current_price ?? 0;

  const longLiq = long?.liquidation_price ?? 0;
  const shortLiq = short?.liquidation_price ?? 0;
  let min = longLiq ? longLiq * 0.95 : current * 0.8;
  let max = shortLiq ? shortLiq * 1.05 : current * 1.2;
  if (min > max) [min, max] = [max, min];

  const [price, setPrice] = useState<number>(current || min);

  const { data: evaluation } = useHedgeEvaluation(selected, price);

  if (!hedges.length) return null;

  return (
    <div className="hedge-labs-container mt-4">
      <div className="d-flex align-items-center mb-3">
        <select
          id="hedgeSelect"
          value={selected ?? ''}
          onChange={e => setSelected(e.target.value)}
        >
          {hedges.map(h => (
            <option key={h.id} value={h.id}>
              Hedge #{h.id}
            </option>
          ))}
        </select>
      </div>

      <input
        id="priceSlider"
        type="range"
        disabled={!positions.length}
        min={min}
        max={max}
        step={0.01}
        value={price}
        onChange={e => setPrice(parseFloat(e.target.value))}
        style={{ width: '100%' }}
      />
      <div id="priceValue" className="text-center my-2">
        Price: ${price.toFixed(2)}
      </div>

      <table id="evalTable" className="table hedge-labs-table table-striped mt-3">
        <thead>
          <tr>
            <th>Side</th>
            <th>Value</th>
            <th>Travel %</th>
            <th>Liq Dist</th>
            <th>Heat</th>
          </tr>
        </thead>
        <tbody>
          {['long', 'short'].map(side => {
            const row = (evaluation as any)?.[side];
            if (!row) return null;
            return (
              <tr key={side}>
                <td>{side}</td>
                <td>{row.value.toFixed(2)}</td>
                <td>{row.travel_percent.toFixed(2)}</td>
                <td>{row.liquidation_distance.toFixed(2)}</td>
                <td>{row.heat_index.toFixed(2)}</td>
              </tr>
            );
          })}
          {evaluation?.totals && (
            <tr>
              <th>Total</th>
              <th>{evaluation.totals.total_value.toFixed(2)}</th>
              <th>{evaluation.totals.avg_travel_percent.toFixed(2)}</th>
              <th>
                {['long', 'short']
                  .map(s => (evaluation as any)?.[s]?.liquidation_distance)
                  .filter((v): v is number => typeof v === 'number')
                  .reduce((a, b, _, arr) => a + b / arr.length, 0)
                  .toFixed(2)}
              </th>
              <th>{evaluation.totals.avg_heat_index.toFixed(2)}</th>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
