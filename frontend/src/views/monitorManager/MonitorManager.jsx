
import React, { useEffect, useState, useCallback } from 'react';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';
import axios from 'utils/axios';
import { Box, Typography, Snackbar, Alert, Button } from '@mui/material';
import { getProfitCfg, saveProfitCfg } from 'api/profitMonitor';

import LiquidationMonitorCard from './LiquidationMonitorCard';
import ProfitMonitorCard from './ProfitMonitorCard';
import SonicMonitorCard from './SonicMonitorCard';
import MarketMonitorCard from './MarketMonitorCard';

/* ------------------------------------------------------------------ */
/* Layout constants — keep cards compact but tall enough for bars */
/* ------------------------------------------------------------------ */
export const COLUMN_A_WIDTH = 450; // px
export const COLUMN_B_WIDTH = 480; // px
export const ROW_A_MIN = 420; // px
export const ROW_B_MIN = 430; // px (reduced; prevents overstretch)
export const GRID_GAP = 24; // px
/* ------------------------------------------------------------------ */

export default function MonitorManager() {
  useSonicStatusPolling();
  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [marketCfg, setMarketCfg] = useState({});
  const [pctMoves, setPctMoves] = useState({});
  const [loopSec, setLoopSec] = useState('');
  const [nearestLiq, setNearestLiq] = useState({});
  const [toast, setToast] = useState(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const markDirty = useCallback((setter) => (value) => {
    setDirty(true);
    setter(value);
  }, []);

  /* ------------------------- initial fetch ------------------------------- */
  useEffect(() => {
    axios.get('/api/monitor-settings/liquidation').then((r) => setLiqCfg(r.data));
    getProfitCfg().then((cfg) => setProfitCfg(cfg));
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
  const saveAll = useCallback(async () => {
    setSaving(true);
    try {
      await axios.post('/api/monitor-settings/liquidation', liqCfg);
      await saveProfitCfg({
        enabled: profitCfg?.enabled,
        position_profit_usd: Number(profitCfg?.position_profit_usd ?? 0),
        portfolio_profit_usd: Number(profitCfg?.portfolio_profit_usd ?? 0),
        notifications: profitCfg?.notifications
      });
      await axios.post('/api/monitor-settings/market', marketCfg);
      await axios.post('/api/monitor-settings/sonic', {
        interval_seconds: parseInt(loopSec || '0', 10),
        enabled_sonic: liqCfg.enabled_sonic,
        enabled_liquid: liqCfg.enabled_liquid,
        enabled_profit: liqCfg.enabled_profit,
        enabled_market: liqCfg.enabled_market
      });
      setToast({ message: 'Settings saved', severity: 'success' });
      setDirty(false);
    } catch (err) {
      setToast({ message: 'Failed to save settings', severity: 'error' });
    } finally {
      setSaving(false);
    }
  }, [liqCfg, loopSec, marketCfg, profitCfg]);

  /* ----------------------------- render ---------------------------------- */
  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Monitor Manager
      </Typography>

      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-start' }}>
        <Button
          variant="contained"
          color={dirty ? 'success' : 'primary'}
          onClick={saveAll}
          disabled={!dirty || saving}
          sx={{ fontWeight: 'bold', textTransform: 'none' }}
        >
          {saving ? 'Saving…' : 'Save All'}
        </Button>
      </Box>

      {/* 2×2 card grid with flexible row heights (minmax) */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: `${COLUMN_A_WIDTH}px ${COLUMN_B_WIDTH}px`,
          gridTemplateRows: `minmax(${ROW_A_MIN}px, auto) minmax(${ROW_B_MIN}px, auto)`,
          gap: `${GRID_GAP}px`,
          width: '100%',
          boxSizing: 'border-box'
        }}
      >
        {/* Row A / Col A */}
        <Box sx={{ gridColumn: 1, gridRow: 1 }}>
          <SonicMonitorCard
            cfg={liqCfg}
            setCfg={markDirty(setLiqCfg)}
            loop={loopSec}
            setLoop={markDirty(setLoopSec)}
          />
        </Box>

        {/* Row A / Col B */}
        <Box sx={{ gridColumn: 2, gridRow: 1 }}>
          <LiquidationMonitorCard
            cfg={liqCfg}
            setCfg={markDirty(setLiqCfg)}
            blast={marketCfg.blast_radius}
            nearest={nearestLiq}
            disabled={!liqCfg.enabled_sonic || !liqCfg.enabled_liquid}
          />
        </Box>

        {/* Row B / Col A */}
        <Box sx={{ gridColumn: 1, gridRow: 2 }}>
          <ProfitMonitorCard
            cfg={profitCfg}
            setCfg={markDirty(setProfitCfg)}
            disabled={!liqCfg.enabled_sonic || !liqCfg.enabled_profit}
          />
        </Box>

        {/* Row B / Col B */}
        <Box sx={{ gridColumn: 2, gridRow: 2 }}>
          <MarketMonitorCard
            cfg={marketCfg}
            setCfg={markDirty(setMarketCfg)}
            live={pctMoves}
            disabled={!liqCfg.enabled_sonic || !liqCfg.enabled_market}
          />
        </Box>
      </Box>

      <Snackbar
        open={!!toast?.message}
        autoHideDuration={3000}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={toast?.severity || 'success'}>{toast?.message}</Alert>
      </Snackbar>
    </Box>
  );
}
