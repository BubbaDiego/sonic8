import React, { useMemo, useState } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  Stack,
  Tooltip,
  Typography
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

const LAMPORTS_PER_SOL = 1_000_000_000;

// helper: shorten address
const short = (s, left = 4, right = 4) =>
  !s ? '' : (s.length <= left + right ? s : `${s.slice(0, left)}…${s.slice(-right)}`);

// helper: symbol from mint with small priority set; fallback to short mint
const MINT_SYMBOL = {
  EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v: 'USDC',
  '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs': 'WETH',
  '9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E': 'WBTC'
};
const sym = (mint) => (mint === 'native' ? 'SOL' : (MINT_SYMBOL[mint] || `${mint.slice(0,4)}…${mint.slice(-4)}`));

export default function VerifiedBalancesPanel({ wallets = [] }) {
  const addrs = useMemo(
    () => wallets.map(w => ({ name: w.name, addr: (w.public_address || '').trim() }))
                  .filter(x => x.addr),
    [wallets]
  );

  const [busy, setBusy] = useState(false);
  const [data, setData] = useState({});  // { address -> payload }
  const [err, setErr] = useState('');

  const verifyAll = async () => {
    setBusy(true); setErr('');
    try {
      const res = await fetch('/api/wallets/verify-bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ addresses: addrs.map(x => x.addr) })
      });
      const json = await res.json();
      setData(json || {});
    } catch (e) {
      console.error(e);
      setErr('Failed to verify balances.');
    } finally {
      setBusy(false);
    }
  };

  const rows = useMemo(() => {
    // build a render-friendly list; prefer totals.solIncludingRent
    return addrs.map(({ name, addr }) => {
      const v = data[addr];
      const verified = v && !v.error ? (v.totals?.solIncludingRent ?? (v.sol?.lamports || 0) / LAMPORTS_PER_SOL) : null;
      const top = v?.top || [];
      return { name, addr, verified, top };
    });
  }, [addrs, data]);

  return (
    <MainCard sx={{ mt: 2 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="h4">Verified (On-Chain)</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          {busy && <CircularProgress size={20} />}
          <Button onClick={verifyAll} variant="contained" size="small" disabled={busy || !addrs.length}>
            Verify all
          </Button>
        </Stack>
      </Stack>

      {!!err && <Typography color="error" variant="body2" sx={{ mb: 1 }}>{err}</Typography>}
      {!addrs.length && <Typography variant="body2">No wallets found.</Typography>}

      <Grid container spacing={1}>
        {rows.map((r) => (
          <Grid key={r.addr} item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Stack>
                    <Typography variant="subtitle2">{r.name}</Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="caption" color="text.secondary">{short(r.addr, 6, 6)}</Typography>
                      <Tooltip title="Copy address">
                        <IconButton size="small" onClick={() => navigator.clipboard.writeText(r.addr)}>
                          <ContentCopyIcon fontSize="inherit" />
                        </IconButton>
                      </Tooltip>
                      <Button size="small" variant="text" href={`https://solscan.io/account/${r.addr}`} target="_blank" rel="noreferrer">
                        Solscan
                      </Button>
                    </Stack>
                  </Stack>

                  <Box textAlign="right">
                    {r.verified == null ? (
                      <Typography variant="body2" color="text.secondary">— not verified —</Typography>
                    ) : (
                      <>
                        <Typography variant="h6">{Number(r.verified).toFixed(9)} SOL</Typography>
                        <Typography variant="caption" color="text.secondary">incl. token-acct rent</Typography>
                      </>
                    )}
                  </Box>
                </Stack>

                {r.top?.length > 0 && (
                  <>
                    <Divider sx={{ my: 1 }} />
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {r.top.slice(0, 4).map((t, i) => (
                        <Chip key={i}
                          size="small"
                          label={`${sym(t.mint)}: ${t.amount}`}
                          variant={t.symbol === 'SOL' ? 'filled' : 'outlined'}
                        />
                      ))}
                    </Stack>
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </MainCard>
  );
}

