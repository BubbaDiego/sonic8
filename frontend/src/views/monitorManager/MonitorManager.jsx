/* MonitorManager.jsx – UI page for adjusting monitor thresholds.
   Uses React + MUI (v5) and axios for API calls.
*/
import React, { useEffect, useState } from 'react';
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
  Typography
} from '@mui/material';

function LiquidationSettings({ cfg, setCfg }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    setCfg(prev => ({ ...prev, [name]: value }));
  };
  return (
    <Card variant='outlined'>
      <CardHeader title='Liquidation Monitor' subheader='Global threshold & snooze' />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Threshold %'
              name='threshold_percent'
              value={cfg.threshold_percent ?? ''}
              onChange={handleChange}
              type='number'
              inputProps={{ step: '0.1' }}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              label='Snooze (seconds)'
              name='snooze_seconds'
              value={cfg.snooze_seconds ?? ''}
              onChange={handleChange}
              type='number'
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

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