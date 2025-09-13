// frontend/src/components/jupiter/Perps/PositionsPanel.jsx
import { useQuery } from '@tanstack/react-query';
import { perpsPositions } from 'api/jupiter.perps';
import { whoami } from 'api/jupiter';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Typography } from '@mui/material';

export default function PositionsPanel() {
  const me = useQuery({ queryKey: ['whoami-perps'], queryFn: whoami, staleTime: 5_000, retry: 0 });
  const owner = me.data?.pubkey;
  const q = useQuery({
    queryKey: ['perpsPositions', owner],
    queryFn: () => perpsPositions(owner),
    enabled: !!owner,
    staleTime: 5_000,
    refetchOnWindowFocus: false
  });

  return (
    <MainCard title="Perps · My Positions">
      {!owner && <Typography>Loading wallet…</Typography>}
      {owner && q.isLoading && <Typography>Loading positions…</Typography>}
      {owner && q.isError && <Typography color="error">Error: {q.error?.message}</Typography>}
      {owner && q.isSuccess && (
        <Box sx={{ fontFamily: 'ui-monospace, Menlo, Consolas, monospace', fontSize: 12 }}>
          <div>owner: <code>{owner}</code></div>
          <div>count: {q.data.count}</div>
          <hr />
          {(q.data.items || []).slice(0, 30).map((p) => (
            <div key={p.pubkey} style={{ marginBottom: 8 }}>
              <b>{p.pubkey}</b> · owner={String(p.owner || '—')}
              {/* when we map actual fields from IDL we’ll format size/price/side here */}
            </div>
          ))}
          <Typography variant="caption" color="textSecondary">
            This is a raw decode preview. Next pass: PnL, borrow/funding breakdown, liq price.
          </Typography>
        </Box>
      )}
    </MainCard>
  );
}
