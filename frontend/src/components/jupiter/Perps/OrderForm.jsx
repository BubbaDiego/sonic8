import React, { useState } from 'react';
import {
  Button,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
  FormControlLabel,
  Switch
} from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import { useSnackbar } from 'notistack';
import { createPerpOrder, closePerpPosition } from 'api/jupiter.perps';

const SIDES = [
  { label: 'Long', value: 'long' },
  { label: 'Short', value: 'short' }
];

const DEFAULT_MARKETS = [
  { label: 'SOL-PERP', value: 'SOL-PERP' },
  { label: 'BTC-PERP', value: 'BTC-PERP' },
  { label: 'ETH-PERP', value: 'ETH-PERP' }
];

export default function OrderForm({ defaultMarket = 'SOL-PERP' }) {
  const { enqueueSnackbar } = useSnackbar();

  const [market, setMarket] = useState(defaultMarket);
  const [side, setSide] = useState('long');
  const [sizeUsd, setSizeUsd] = useState('100');         // notional in USD
  const [collateralUsd, setCollateralUsd] = useState('20'); // collateral in USD
  const [useTp, setUseTp] = useState(false);
  const [useSl, setUseSl] = useState(false);
  const [tpPrice, setTpPrice] = useState('');
  const [slPrice, setSlPrice] = useState('');
  const [sending, setSending] = useState(false);

  async function onOpen() {
    try {
      setSending(true);
      const payload = {
        market,
        side, // 'long' | 'short'
        sizeUsd: Number(sizeUsd),
        collateralUsd: Number(collateralUsd),
        tp: useTp && tpPrice ? Number(tpPrice) : null,
        sl: useSl && slPrice ? Number(slPrice) : null
      };
      if (!payload.sizeUsd || payload.sizeUsd <= 0) throw new Error('Size (USD) must be > 0');
      if (!payload.collateralUsd || payload.collateralUsd <= 0) throw new Error('Collateral (USD) must be > 0');

      const res = await createPerpOrder(payload);
      const label = res?.requestId || res?.signature || 'submitted';
      enqueueSnackbar(`Perp order submitted: ${label}`, { variant: 'success' });
    } catch (e) {
      enqueueSnackbar(e?.message || String(e), { variant: 'error' });
    } finally {
      setSending(false);
    }
  }

  async function onClose() {
    try {
      setSending(true);
      const res = await closePerpPosition({ market });
      const label = res?.requestId || res?.signature || 'submitted';
      enqueueSnackbar(`Close request submitted: ${label}`, { variant: 'success' });
    } catch (e) {
      enqueueSnackbar(e?.message || String(e), { variant: 'error' });
    } finally {
      setSending(false);
    }
  }

  return (
    <MainCard title="Perps — Order">
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            select
            label="Market"
            value={market}
            onChange={(e) => setMarket(e.target.value)}
          >
            {DEFAULT_MARKETS.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            select
            fullWidth
            label="Side"
            value={side}
            onChange={(e) => setSide(e.target.value)}
          >
            {SIDES.map((s) => (
              <MenuItem key={s.value} value={s.value}>
                {s.label}
              </MenuItem>
            ))}
          </TextField>
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="Size (USD)"
            value={sizeUsd}
            onChange={(e) => setSizeUsd(e.target.value)}
            inputProps={{ inputMode: 'decimal' }}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="Collateral (USD)"
            value={collateralUsd}
            onChange={(e) => setCollateralUsd(e.target.value)}
            inputProps={{ inputMode: 'decimal' }}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <FormControlLabel
            control={<Switch checked={useTp} onChange={(e) => setUseTp(e.target.checked)} />}
            label="Take Profit"
          />
          <TextField
            fullWidth
            label="TP Price"
            value={tpPrice}
            onChange={(e) => setTpPrice(e.target.value)}
            disabled={!useTp}
            inputProps={{ inputMode: 'decimal' }}
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <FormControlLabel
            control={<Switch checked={useSl} onChange={(e) => setUseSl(e.target.checked)} />}
            label="Stop Loss"
          />
          <TextField
            fullWidth
            label="SL Price"
            value={slPrice}
            onChange={(e) => setSlPrice(e.target.value)}
            disabled={!useSl}
            inputProps={{ inputMode: 'decimal' }}
          />
        </Grid>

        <Grid item xs={12}>
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={onOpen} disabled={sending}>
              Open
            </Button>
            <Button variant="outlined" onClick={onClose} disabled={sending}>
              Close
            </Button>
          </Stack>
          <Typography variant="caption" color="textSecondary">
            Orders are submitted as on-chain <em>requests</em>; Jupiter keepers execute shortly after.
          </Typography>
        </Grid>
      </Grid>
    </MainCard>
  );
}
