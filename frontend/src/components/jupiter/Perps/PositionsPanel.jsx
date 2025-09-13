import { useQuery } from '@tanstack/react-query';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Button, Typography } from '@mui/material';

// tiny fetchers (same rationale as MarketsPanel)
async function http(path) {
  const res = await fetch(path);
  const t = await res.text();
  const j = t ? JSON.parse(t) : {};
  if (!res.ok) throw new Error(j.detail || j.message || `HTTP ${res.status}`);
  return j;
}
const fetchOwner = () => http('/api/jupiter/whoami');
const fetchPositions = (owner) => http(`/api/perps/positions?owner=${encodeURIComponent(owner)}`);

export default function PositionsPanel() {
  const me = useQuery({ queryKey:['perpsWhoami'], queryFn: fetchOwner, staleTime: 5000, retry: 0 });
  const owner = me.data?.pubkey;

  const q = useQuery({
    queryKey: ['perpsPositions', owner],
    queryFn: () => fetchPositions(owner),
    enabled: !!owner,
    staleTime: 5000
  });

  return (
    <MainCard title="Perps · My Positions" secondary={<Button size="small" onClick={() => q.refetch()} disabled={!owner}>Refresh</Button>}>
      {!owner && <Typography>Loading wallet…</Typography>}
      {owner && q.isLoading && <Typography>Loading positions…</Typography>}
      {owner && q.isError && <Typography color="error">Error: {q.error?.message}</Typography>}
      {owner && q.isSuccess && (
        <Box sx={{ fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <div>owner: <code>{owner}</code></div>
          <div>count: {q.data.count ?? 0}</div>
          <hr />
          {(q.data.items || []).length === 0 && <Typography>No open positions.</Typography>}
          {(q.data.items || []).slice(0, 30).map(p => (
            <div key={p.pubkey} style={{ marginBottom: 8 }}>
              <b>{p.pubkey}</b> · owner={String(p.owner || '—')}
            </div>
          ))}
          <Typography variant="caption" color="textSecondary">
            Raw decode preview. Next pass adds PnL, borrow/funding fees, liq price.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
