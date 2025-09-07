import { Chip, Stack, Typography, CircularProgress, Tooltip } from '@mui/material';

const MONO = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' };
const LAMPORTS_PER_SOL = 1000000000;

const MINT_SYMBOL = {
  EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v: 'USDC',
  '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs': 'WETH',
  '9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E': 'WBTC'
};
const sym = (mint) => (mint === 'native' ? 'SOL' : (MINT_SYMBOL[mint] || `${mint.slice(0,4)}…${mint.slice(-4)}`));

export function VerifiedSolCell({ value, rentLamports, loading }) {
  if (loading) return <CircularProgress size={18} />;
  if (value == null) return <Typography variant="body2" color="text.secondary">— not verified —</Typography>;
  return (
    <Stack alignItems="flex-end" spacing={0}>
      <Typography variant="subtitle2" sx={MONO}>{Number(value).toFixed(9)} SOL</Typography>
      <Typography variant="caption" color="text.secondary">
        incl. rent • {(rentLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL
      </Typography>
    </Stack>
  );
}

export function TopTokensChips({ top = [], limit = 4 }) {
  if (!top.length) return <Typography variant="caption" color="text.secondary">—</Typography>;
  const shown = top.slice(0, limit);
  const more = Math.max(0, top.length - shown.length);
  return (
    <Stack direction="row" spacing={0.75} flexWrap="wrap">
      {shown.map((t, i) => (
        <Chip key={i}
          size="small"
          label={`${sym(t.mint)} ${t.amount}`}
          variant={t.symbol === 'SOL' ? 'filled' : 'outlined'}
        />
      ))}
      {more > 0 && <Chip size="small" label={`+${more} more`} variant="outlined" />}
    </Stack>
  );
}

export function VerifiedStatusCell({ verifiedAt, error, detail, staleMs = 10 * 60 * 1000 }) {
  if (error) return (
    <Tooltip title={detail || error}>
      <Chip color="error" size="small" label="Error" />
    </Tooltip>
  );
  if (!verifiedAt) return <Chip variant="outlined" size="small" label="Not verified" />;
  const age = Date.now() - verifiedAt;
  const stale = age > staleMs;
  const hh = new Date(verifiedAt).toLocaleTimeString();
  const label = stale ? 'Stale' : 'Verified';
  const color = stale ? 'warning' : 'success';
  return (
    <Tooltip title={`Verified at ${hh} • ${Math.round(age / 1000)}s ago`}>
      <Chip color={color} size="small" label={label} />
    </Tooltip>
  );
}
