
import React, { useEffect, useState } from 'react';
import axios from 'utils/axios';
import { Box, Typography, Grid, Snackbar, Alert } from '@mui/material';

import LiquidationMonitorCard from './LiquidationMonitorCard';
import ProfitMonitorCard from './ProfitMonitorCard';
import SonicMonitorCard from './SonicMonitorCard';
import MarketMonitorCard from './MarketMonitorCard';

export default function MonitorManager() {
  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [marketCfg, setMarketCfg] = useState({});
  const [pctMoves, setPctMoves] = useState({});
  const [loopSec, setLoopSec] = useState('');
  const [nearestLiq, setNearestLiq] = useState({});
  const [toast, setToast] = useState('');

  /* ------------------------- initial fetch ------------------------------- */
  useEffect(() => {
    axios.get('/api/monitor-settings/liquidation').then((r) => setLiqCfg(r.data));
    axios.get('/api/monitor-settings/profit').then((r) => setProfitCfg(r.data));
    axios.get('/api/monitor-settings/market').then((r) => setMarketCfg(r.data));
    axios.get('/api/market/latest').then((r) => setPctMoves(r.data));
    axios.get('/api/monitor-settings/sonic').then((r) => {
      setLoopSec(String(r.data.interval_seconds ?? ''));
      setLiqCfg((prev) => ({ ...prev, ...r.data }));
    });

    axios
      .get('/api/liquidation/nearest-distance')
      .then((r) => setNearestLiq(r.data))
      .catch(() => setNearestLiq({}));
  }, []);

  /* ---------------------------- handlers --------------------------------- */
  const saveAll = async () => {
    await axios.post('/api/monitor-settings/liquidation', liqCfg);
    await axios.post('/api/monitor-settings/profit', profitCfg);
    await axios.post('/api/monitor-settings/market', marketCfg);
    await axios.post('/api/monitor-settings/sonic', {
      interval_seconds: parseInt(loopSec || '0', 10),
      enabled_sonic: liqCfg.enabled_sonic,
      enabled_liquid: liqCfg.enabled_liquid,
      enabled_profit: liqCfg.enabled_profit,
      enabled_market: liqCfg.enabled_market
    });
    setToast('Settings saved');
  };

  /* ----------------------------- render ---------------------------------- */
  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Monitor Manager
      </Typography>

      <Grid container spacing={3}>
        {/* ---------- 1st Row ---------- */}
        <Grid item xs={12} md={6}>
          <SonicMonitorCard
            cfg={liqCfg}
            setCfg={setLiqCfg}
            loop={loopSec}
            setLoop={setLoopSec}
            saveAll={saveAll}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <LiquidationMonitorCard
            cfg={liqCfg}
            setCfg={setLiqCfg}
            blast={marketCfg.blast_radius}
            nearest={nearestLiq}
          />
        </Grid>

        {/* ---------- 2nd Row ---------- */}
        <Grid item xs={12} md={6}>
          <ProfitMonitorCard cfg={profitCfg} setCfg={setProfitCfg} />
        </Grid>
        <Grid item xs={12} md={6}>
          <MarketMonitorCard cfg={marketCfg} setCfg={setMarketCfg} live={pctMoves} />
        </Grid>
      </Grid>

      <Snackbar
        open={!!toast}
        autoHideDuration={3000}
        onClose={() => setToast('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="success">{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
