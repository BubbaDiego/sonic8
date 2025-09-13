// frontend/src/components/jupiter/Perps/MarketsPanel.jsx
import { useQuery } from '@tanstack/react-query';
import { perpsMarkets } from 'api/jupiter.perps';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Typography } from '@mui/material';

export default function MarketsPanel() {
  const q = useQuery({ queryKey: ['perpsMarkets'], queryFn: perpsMarkets, staleTime: 10_000, refetchOnWindowFocus: false });

  return (
    <MainCard title="Perps · Markets">
      {q.isLoading && <Typography>Loading markets…</Typography>}
      {q.isError && <Typography color="error">Error: {q.error?.message}</Typography>}
      {q.isSuccess && (
        <Box sx={{ maxHeight: 360, overflowY: 'auto', fontFamily: 'ui-monospace, Menlo, Consolas, monospace', fontSize: 12 }}>
          <div>pools: {q.data.poolsCount} · custodies: {q.data.custodiesCount}</div>
          <hr />
          <div><b>Pools (raw, compact)</b></div>
          <ul>
            {(q.data.pools || []).slice(0, 20).map((p) => (
              <li key={p.pubkey}><code>{p.pubkey}</code></li>
            ))}
          </ul>
          <div><b>Custodies (token mints)</b></div>
          <ul>
            {(q.data.custodies || []).slice(0, 50).map((c) => (
              <li key={c.pubkey}><code>{c.pubkey}</code> · mint={String(c.mint || '—')} · dec={String(c.decimals ?? '—')}</li>
            ))}
          </ul>
          <Typography variant="caption" color="textSecondary">
            This is a first read‑only slice. Next pass: funding, OI, fee previews.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
