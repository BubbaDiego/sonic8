import React, { useEffect, useState, useMemo } from 'react';
import axios from 'utils/axios';
import {
  Box, Card, CardContent, CardHeader, TextField, Grid,
  Button, Snackbar, Alert, Typography, ToggleButton,
  ToggleButtonGroup, Stack, CircularProgress
} from '@mui/material';

import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import CurrencyExchangeIcon from '@mui/icons-material/CurrencyExchange';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';

// Asset Icons
const ASSETS = [
  { code: 'BTC', Icon: CurrencyBitcoinIcon },
  { code: 'ETH', Icon: AccountBalanceWalletIcon },
  { code: 'SOL', Icon: CurrencyExchangeIcon }
];

// Circular Countdown Component
function CircularCountdown({ remaining, total }) {
  const percent = (remaining / total) * 100;

  return (
    <Box sx={{ position: 'relative', display: 'inline-flex', mt: 2 }}>
      <CircularProgress variant="determinate" value={percent} size={80} thickness={4} />
      <Box
        sx={{
          top: 0, left: 0, bottom: 0, right: 0,
          position: 'absolute', display: 'flex',
          alignItems: 'center', justifyContent: 'center'
        }}
      >
        <Typography variant="h6" component="div" color="text.secondary">
          {remaining}s
        </Typography>
      </Box>
    </Box>
  );
}

// Liquidation Monitor Card
function LiquidationSettings({ cfg = {}, setCfg }) {
  const [remaining, setRemaining] = useState(0);
  const [isCounting, setIsCounting] = useState(false);

  const normCfg = useMemo(() => ({
    threshold_percent: cfg.threshold_percent ?? '',
    snooze_seconds: cfg.snooze_seconds ?? '',
    thresholds: { BTC: '', ETH: '', SOL: '', ...(cfg.thresholds || {}) },
    notifications: { system: true, voice: true, sms: false, ...(cfg.notifications || {}) }
  }), [cfg]);

  useEffect(() => {
    let timer;
    if (isCounting && remaining > 0) {
      timer = setInterval(() => {
        setRemaining(prev => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    } else if (remaining === 0) {
      setIsCounting(false);
    }
    return () => clearInterval(timer);
  }, [isCounting, remaining]);

  const startSnooze = () => {
    const duration = parseInt(normCfg.snooze_seconds, 10);
    if (duration > 0) {
      setRemaining(duration);
      setIsCounting(true);
    }
  };

  // Handlers
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

  return (
    <Card variant='outlined'>
      <CardHeader title='Liquidation Monitor' subheader='Global threshold & snooze' />
      <CardContent>
        <Grid container spacing={2}>
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

          <Grid item xs={12}>
            {isCounting ? (
              <CircularCountdown remaining={remaining} total={normCfg.snooze_seconds} />
            ) : (
              <Button variant="outlined" onClick={startSnooze}>
                Start Snooze Countdown
              </Button>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// Profit Monitor Card (unchanged)
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
          {['single_high', 'portfolio_high', 'single_low', 'portfolio_low'].map((field, idx) => (
            <Grid key={field} item xs={6}>
              <TextField
                fullWidth
                label={`${field.replace('_', ' ').toUpperCase()} ($)`}
                name={field}
                value={cfg[field] ?? ''}
                onChange={handleChange}
                type='number'
              />
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}

// Outer page wrapper
export default function MonitorManager() {
  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [toast, setToast] = useState('');

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
        <Alert severity='success'>{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
