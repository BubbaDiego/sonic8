/* MonitorManager.jsx – Liquidation & Profit monitor configuration page.
   v2 – July 2025
   • Liquidation card more compact: asset rows with icons stacked vertically.
   • New notification selector (System, Voice, SMS) wired to nested `notifications` dict.
   • Payload shape:
       {
         threshold_percent,
         snooze_seconds,
         thresholds: { BTC, ETH, SOL },
         notifications: { system, voice, sms }
       }
*/

import React, { useEffect, useState, useMemo } from 'react';
import axios from 'utils/axios';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  TextField,
  Grid,
  Button,
  Snackbar,
  Alert,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Stack
} from '@mui/material';
import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import CurrencyEthereumIcon from '@mui/icons-material/CurrencyEthereum';
import CurrencyExchangeIcon from '@mui/icons-material/CurrencyExchange';

const ASSETS = [
  { code: 'BTC', Icon: CurrencyBitcoinIcon },
  { code: 'ETH', Icon: CurrencyEthereumIcon },
  { code: 'SOL', Icon: CurrencyExchangeIcon }
];

// -----------------------------------------------------------
// Liquidation Monitor Card
// -----------------------------------------------------------
function LiquidationSettings({ cfg = {}, setCfg }) {
  /* Normalise state shape */
  const normCfg = useMemo(() => ({
    threshold_percent: cfg.threshold_percent ?? '',
    snooze_seconds: cfg.snooze_seconds ?? '',
    thresholds: { BTC: '', ETH: '', SOL: '', ...(cfg.thresholds || {}) },
    notifications: { system: true, voice: true, sms: false, ...(cfg.notifications || {}) }
  }), [cfg]);

  // --- Handlers ----------------------------------------------------
  const handleGlobalChange = (e) => {
    const { name, value } = e.target;
    setCfg(prev => ({ ...prev, [name]: value }));
  };

  const handleThresholdChange = (asset) => (e) => {
    const value = e.target.value;
    setCfg(prev => ({
      ...prev,
      thresholds: { ...(prev.thresholds || {}), [asset]: value }
    }));
  };

  const handleNotifChange = (event, selections) => {
    setCfg(prev => ({
      ...prev,
      notifications: {
        system: selections.includes('system'),
        voice: selections.includes('voice'),
        sms: selections.includes('sms')
      }
    }));
  };

  const selectedNotifs = Object.entries(normCfg.notifications)
    .filter(([k, v]) => v)
    .map(([k]) => k);

  // --- Render ------------------------------------------------------
  return (
    <Card variant='outlined'>
      <CardHeader title='Liquidation Monitor' subheader='Global threshold & snooze' />
      <CardContent>
        <Grid container spacing={2}>
          {/* Global fields */}
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label='Threshold %'
              name='threshold_percent'
              value={normCfg.threshold_percent}
              onChange={handleGlobalChange}
              type='number'
              inputProps={{ step: '0.1' }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label='Snooze (seconds)'
              name='snooze_seconds'
              value={normCfg.snooze_seconds}
              onChange={handleGlobalChange}
              type='number'
            />
          </Grid>

          {/* Asset‑specific thresholds */}
          <Grid item xs={12} md={6}>
            {ASSETS.map(({ code, Icon }) => (
              <Stack key={code} direction='row' spacing={1} alignItems='center' sx={{ mb: 1 }}>
                <Icon fontSize='small' />
                <TextField
                  fullWidth
                  label={`${code} Threshold`}
                  value={normCfg.thresholds[code]}
                  onChange={handleThresholdChange(code)}
                  type='number'
                  size='small'
                />
              </Stack>
            ))}
          </Grid>

          {/* Notification toggle buttons */}
          <Grid item xs={12} md={6}>
            <Typography variant='subtitle2' gutterBottom>Notifications</Typography>
            <ToggleButtonGroup
              value={selectedNotifs}
              onChange={handleNotifChange}
              aria-label='notification types'
              size='small'
            >
              <ToggleButton value='system'>System</ToggleButton>
              <ToggleButton value='voice'>Voice</ToggleButton>
              <ToggleButton value='sms'>SMS</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// -----------------------------------------------------------
// Profit Monitor Card (unchanged)
// -----------------------------------------------------------
function ProfitSettings({ cfg, setCfg }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    setCfg(prev => ({ ...prev, [name]: value }));
  };
  return (
    <Card variant='outlined'>
      <CardHeader title='Profit Monitor' subheader='Single & portfolio profit thresholds' />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Single Profit HIGH ($)'
              name='single_high'
              value={cfg.single_high ?? ''}
              onChange={handleChange}
              type='number'
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Portfolio Profit HIGH ($)'
              name='portfolio_high'
              value={cfg.portfolio_high ?? ''}
              onChange={handleChange}
              type='number'
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Single Profit LOW ($)'
              name='single_low'
              value={cfg.single_low ?? ''}
              onChange={handleChange}
              type='number'
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Portfolio Profit LOW ($)'
              name='portfolio_low'
              value={cfg.portfolio_low ?? ''}
              onChange={handleChange}
              type='number'
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// -----------------------------------------------------------
// Outer page wrapper
// -----------------------------------------------------------
export default function MonitorManager() {
  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [toast, setToast] = useState('');

  // Fetch on mount
  useEffect(() => {
    axios.get('/api/monitor-settings/liquidation').then(r => setLiqCfg(r.data));
    axios.get('/api/monitor-settings/profit').then(r => setProfitCfg(r.data));
  }, []);

  const save = async () => {
    await axios.post('/api/monitor-settings/liquidation', liqCfg);
    await axios.post('/api/monitor-settings/profit', profitCfg);
    setToast('Settings saved');
  };

  return (
    <Box p={3}>
      <Typography variant='h4' gutterBottom>Monitor Manager</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <LiquidationSettings cfg={liqCfg} setCfg={setLiqCfg} />
        </Grid>
        <Grid item xs={12} md={6}>
          <ProfitSettings cfg={profitCfg} setCfg={setProfitCfg} />
        </Grid>
        <Grid item xs={12}>
          <Button variant='contained' color='primary' onClick={save}>
            Save All
          </Button>
        </Grid>
      </Grid>

      <Snackbar
        open={!!toast}
        autoHideDuration={3000}
        onClose={() => setToast('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity='success' sx={{ width: '100%' }}>{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
