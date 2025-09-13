import { useQuery } from '@tanstack/react-query';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Button, Typography } from '@mui/material';

// simple fetch wrapper so we don't couple with your other api files
async function http(path) {
  const res = await fetch(path);
  const t = await res.text();
  const j = t ? JSON.parse(t) : {};
  if (!res.ok) throw new Error(j.detail || j.message || `HTTP ${res.status}`);
  return j;
}
const fetchMarkets = () => http('/api/perps/markets');

export default function MarketsPanel() {
  const q = useQuery({ queryKey: ['perpsMarkets'], queryFn: fetchMarkets, staleTime: 10_000 });

  return (
    <MainCard title="Perps · Markets" secondary={<Button size="small" onClick={() => q.refetch()}>Refresh</Button>}>
      {q.isLoading && <Typography>Loading markets…</Typography>}
      {q.isError && <Typography color="error">Error: {q.error?.message}</Typography>}
      {q.isSuccess && (
        <Box sx={{ maxHeight: 360, overflowY: 'auto', fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <div>accounts in IDL: {(q.data.accounts || []).join(', ') || '—'}</div>
          <div>pools: {q.data.poolsCount ?? 0} · custodies: {q.data.custodiesCount ?? 0}</div>
          <hr />
          <Typography variant="subtitle2">Pools</Typography>
          <ul>
            {(q.data.pools || []).slice(0, 20).map(p => (
              <li key={p.pubkey}><code>{p.pubkey}</code></li>
            ))}
          </ul>
          <Typography variant="subtitle2">Custodies</Typography>
          <ul>
            {(q.data.custodies || []).slice(0, 50).map(c => (
              <li key={c.pubkey}>
                <code>{c.pubkey}</code> · mint={String(c.mint||'—')} · dec={String(c.decimals ?? '—')}
              </li>
            ))}
          </ul>
          <Typography variant="caption" color="textSecondary">
            Raw view first; next pass we’ll compute funding/OI/fee previews.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
