import { useQuery } from '@tanstack/react-query';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Button, Typography } from '@mui/material';

// helpers
async function http(path) {
  const res = await fetch(path);
  const t = await res.text();
  let j = {};
  try { j = t ? JSON.parse(t) : {}; } catch { /* ignore */ }
  if (!res.ok) throw new Error(j.detail || j.message || `HTTP ${res.status}`);
  return j;
}
const getOwner = () => http('/api/jupiter/whoami');
const getDetail = (owner, limit) => http(`/api/perps/positions/detailed?owner=${encodeURIComponent(owner)}&limit=${limit||50}`);

export default function PositionsPanel() {
  const me = useQuery({ queryKey:['perpsWhoami'], queryFn: getOwner, staleTime: 5000, retry: 0 });
  const owner = me.data?.pubkey;
  const q = useQuery({
    queryKey: ['perpsPositionsDetailed', owner],
    queryFn: () => getDetail(owner, 100),
    enabled: !!owner,
    staleTime: 5000
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
                {q.data.items.map((r, i) => (
                  <tr key={i}>
                    <td><code>{(r.pubkey||'').slice(0,6)}…{(r.pubkey||'').slice(-6)}</code></td>
                    <td>{r.side || '—'}</td>
                    <td align="right">{r.size != null ? Number(r.size).toFixed(6) : '—'}</td>
                    <td align="right">{r.entry != null ? Number(r.entry).toFixed(6) : '—'}</td>
                    <td align="right">{r.mark != null ? Number(r.mark).toFixed(6) : '—'}</td>
                    <td align="right" style={{color: r.pnlUsd > 0 ? '#16a34a' : r.pnlUsd < 0 ? '#dc2626' : undefined}}>
                      {r.pnlUsd != null ? (r.pnlUsd >= 0 ? '+' : '') + Number(r.pnlUsd).toFixed(4) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Typography variant="caption" color="textSecondary">
            PnL shown is price-delta only (no fees). Next pass adds borrow/funding/impact fees.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
