import { useQuery } from '@tanstack/react-query';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Button, Typography } from '@mui/material';

async function http(path) {
  const res = await fetch(path);
  const t = await res.text();
  let j = {};
  try { j = t ? JSON.parse(t) : {}; } catch {}
  if (!res.ok) throw new Error(j.detail || j.message || `HTTP ${res.status}`);
  return j;
}
const getOwner = () => http('/api/jupiter/whoami');
// ⬇️  Use the SAME endpoint as the working Positions page: /positions/
//     positions_api.py exposes GET /positions/ returning PositionDB[].
//     We'll shape it into the items that this panel renders.
const getFromDb = async (_owner, limit) => {
  const arr = await http('/positions/');
  // Map DB rows -> UI shape expected here
  const items = (Array.isArray(arr) ? arr : []).slice(0, limit || 100).map((r) => ({
    pubkey: r?.id ?? '',
    side: (r?.position_type || '').toLowerCase(),     // 'long' | 'short'
    size: Number(r?.size ?? 0),
    entry: r?.entry_price != null ? Number(r.entry_price) : null,
    mark:  r?.current_price != null ? Number(r.current_price) : null,
    pnlUsd: r?.pnl_after_fees_usd != null ? Number(r.pnl_after_fees_usd) : 0
  }));
  return { count: items.length, items };
};

export default function PositionsPanel() {
  const me = useQuery({ queryKey:['perpsWhoami'], queryFn:getOwner, staleTime:5000, retry:0 });
  const owner = me.data?.pubkey;
  // Query the DB-backed endpoint just like the main Positions page does.
  const q = useQuery({
    queryKey:['perpsPositionsFromDb', owner],
    queryFn:()=>getFromDb(owner, 100),
    enabled: !!owner,
    staleTime: 3000
  });

  return (
    <MainCard title="Perps · My Positions" secondary={<Button size="small" onClick={()=>q.refetch()} disabled={!owner}>Refresh</Button>}>
      {!owner && <Typography>Loading wallet…</Typography>}
      {owner && q.isLoading && <Typography>Loading positions…</Typography>}
      {owner && q.isError && <Typography color="error">{q.error?.message}</Typography>}
      {owner && q.isSuccess && (
        <Box sx={{ fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <div>owner: <code>{owner}</code></div>
          <div>count: {q.data.count ?? 0}</div>
          <hr />
          {(q.data.items||[]).length === 0 && <Typography>No open positions.</Typography>}
          {(q.data.items||[]).length > 0 && (
            <table width="100%" cellPadding="4" style={{borderCollapse:'collapse'}}>
              <thead>
                <tr>
                  <th align="left">Pubkey</th>
                  <th align="left">Side</th>
                  <th align="right">Size</th>
                  <th align="right">Entry</th>
                  <th align="right">Mark</th>
                  <th align="right">PnL ($)</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((r,i)=>(
                  <tr key={i}>
                    <td><code>{(r.pubkey||'').slice(0,6)}…{(r.pubkey||'').slice(-6)}</code></td>
                    <td>{r.side || '—'}</td>
                    <td align="right">{r.size != null ? Number(r.size).toFixed(6) : '—'}</td>
                    <td align="right">{r.entry != null ? Number(r.entry).toFixed(6) : '—'}</td>
                    <td align="right">{r.mark != null ? Number(r.mark).toFixed(6) : '—'}</td>
                    <td align="right" style={{color: r.pnlUsd > 0 ? '#22c55e' : r.pnlUsd < 0 ? '#ef4444' : undefined}}>
                      {r.pnlUsd != null ? (r.pnlUsd >= 0 ? '+' : '') + Number(r.pnlUsd).toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Typography variant="caption" color="textSecondary">
            PnL is price-delta only (no borrow/funding/impact yet). We’ll add fees next.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
