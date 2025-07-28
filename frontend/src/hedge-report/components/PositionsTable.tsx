import { PositionDB } from '../types/position';
import { useMemo, useState } from 'react';
import btc from '/images/btc_logo.png';
import eth from '/images/eth_logo.png';
import sol from '/images/sol_logo.png';

const icons: Record<string, string> = { BTC: btc, ETH: eth, SOL: sol };

type Col =
  | 'asset'
  | 'collateral'
  | 'value'
  | 'leverage'
  | 'travel_percent'
  | 'size';

const SHORT_COLS: Col[] = [
  'asset',
  'collateral',
  'value',
  'leverage',
  'travel_percent',
  'size'
];
const LONG_COLS: Col[] = [
  'size',
  'travel_percent',
  'leverage',
  'value',
  'collateral',
  'asset'
];
const HEADERS: Record<Col, string> = {
  asset: 'Asset',
  collateral: 'Collateral',
  value: 'Value',
  leverage: 'Leverage',
  travel_percent: 'Travel %',
  size: 'Size'
};

export function PositionsTable({
  positions,
  type
}: {
  positions: PositionDB[];
  type: 'SHORT' | 'LONG';
}) {
  const cols = type === 'SHORT' ? SHORT_COLS : LONG_COLS;
  const [sort, setSort] = useState<{ col: Col; dir: 'asc' | 'desc' }>({
    col: cols[0],
    dir: 'asc'
  });

  const sorted = useMemo(() => {
    const out = [...positions].filter(p => p.position_type === type);
    out.sort((a, b) => {
      const aVal = (a as any)[sort.col];
      const bVal = (b as any)[sort.col];
      const dir = sort.dir === 'asc' ? 1 : -1;
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return dir * (aVal - bVal);
      return dir * String(aVal).localeCompare(String(bVal));
    });
    return out;
  }, [positions, sort, type]);

  function toggle(col: Col) {
    setSort(s =>
      s.col === col ? { ...s, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { col, dir: 'asc' }
    );
  }

  const totals = sorted.reduce(
    (acc, p) => {
      acc.size += p.size;
      acc.value += p.value;
      acc.collateral += p.collateral;
      acc.travel_percent += p.travel_percent;
      acc.leverage += p.leverage;
      return acc;
    },
    {
      size: 0,
      value: 0,
      collateral: 0,
      travel_percent: 0,
      leverage: 0
    }
  );
  const n = sorted.length || 1;

  return (
    <div className="positions-table-wrapper">
      <h3 className="section-title icon-inline text-center mb-2">
        {type === 'SHORT' ? '📉 SHORT' : '📈 LONG'}
      </h3>
      <table
        id={type === 'SHORT' ? 'short-table' : 'long-table'}
        className="positions-table"
      >
        <thead>
          <tr>
            {cols.map(c => (
              <th
                key={c}
                className={['sortable', c === 'asset' ? 'left' : 'center', c === 'size' ? 'size-col' : '']
                  .join(' ')}
                onClick={() => toggle(c)}
              >
                {HEADERS[c]} <span className="sort-indicator" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length ? (
            sorted.map(p => (
              <tr key={p.id}>
                {cols.map(col => {
                  let value: React.ReactNode = (p as any)[col];
                  if (col === 'asset') {
                    value = (
                      <span className="icon-inline">
                        {icons[p.asset_type] && (
                          <img src={icons[p.asset_type]} width={20} />
                        )}
                        {p.asset_type}
                      </span>
                    );
                  } else if (typeof value === 'number') {
                    value =
                      col === 'travel_percent'
                        ? value.toFixed(2) + '%'
                        : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                  }
                  return (
                    <td
                      key={col}
                      className={[
                        col === 'asset' ? 'left' : 'center',
                        col === 'size' ? 'size-col' : ''
                      ].join(' ')}
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))
          ) : (
            <tr className="no-data-row">
              <td colSpan={6} className="no-data">
                No data
              </td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr className="fw-bold">
            {cols.map(col => {
              let content: React.ReactNode = '';
              if (col === 'asset') content = type;
              else if (col === 'travel_percent')
                content = (totals.travel_percent / n).toFixed(2) + '%';
              else if (col === 'leverage')
                content = (totals.leverage / n).toFixed(2);
              else
                content = (totals as any)[col].toLocaleString(undefined, {
                  maximumFractionDigits: 2
                });
              return (
                <td
                  key={col}
                  className={[
                    col === 'asset' ? 'left' : 'center',
                    col === 'size' ? 'size-col' : ''
                  ].join(' ')}
                >
                  {content}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
