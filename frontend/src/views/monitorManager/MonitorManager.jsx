import React, { useEffect, useState, useCallback } from 'react';
import { mutate } from 'swr';
import { Box, Typography, Snackbar, Alert, Button } from '@mui/material';
import axios from 'utils/axios';
import { patchLiquidationSettings } from 'api/monitorSettings';
import useSonicStatusPolling from 'hooks/useSonicStatusPolling';

// profit helpers (present in sonic6; keep same API in 7 if available)
import { getProfitCfg, saveProfitCfg } from 'api/profitMonitor';
import { refreshLatestPortfolio } from 'api/portfolio';
import { refreshActiveSession } from 'api/session';
import { endpoints as statusEP } from 'api/monitorStatus';

import LiquidationMonitorCard from './LiquidationMonitorCard';
import ProfitMonitorCard from './ProfitMonitorCard';
import MarketMonitorCard from './MarketMonitorCard';
import SonicMonitorCard from './SonicMonitorCard';

// Layout constants (mirror sonic6 visual)
export const COLUMN_A_WIDTH = 450; // px
export const GRID_GAP = 24;        // px

export default function MonitorManager() {
  const { sonicActive } = useSonicStatusPolling();

  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [marketCfg, setMarketCfg] = useState({});
  const [nearestLiq, setNearestLiq] = useState({});
  const [pctMoves, setPctMoves] = useState({});
  const [loopSec, setLoopSec] = useState('');

  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState({ open: false, msg: '', sev: 'success' });

  // markDirty wrapper so edits light up "Save All"
  const markDirtySetter = (setter) =>
    (updater) => {
      setDirty(true);
      setter((prev) => (typeof updater === 'function' ? updater(prev) : updater));
    };

  const setLiqCfgDirty    = markDirtySetter(setLiqCfg);
  const setProfitCfgDirty = markDirtySetter(setProfitCfg);
  const setMarketCfgDirty = markDirtySetter(setMarketCfg);
  const setLoopSecDirty   = (value) => {
    setDirty(true);
    setLoopSec(value);
  };

  /* ------------------------- initial bootstrap --------------------------- */
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [
          liqRes,
          profitRes,
          mktRes,
          movesRes,
          sonicRes,
          nearestRes
        ] = await Promise.all([
          axios.get('/api/monitor-settings/liquidation'),
          getProfitCfg().catch(() => ({})),
          axios.get('/api/monitor-settings/market'),
          axios.get('/api/market/latest'),
          axios.get('/api/monitor-settings/sonic'),
          axios.get('/api/liquidation/nearest-distance').catch(() => ({ data: {} }))
        ]);
        if (!alive) return;
        const liq   = liqRes?.data || {};
        const prof  = profitRes   || {};
        const mkt   = mktRes?.data || {};
        const moves = movesRes?.data || {};
        const sonic = sonicRes?.data || {};
        const loop  = String(sonic.interval_seconds ?? '');
        const nearest = nearestRes?.data ?? {};

        // carry Sonic master flags onto liqCfg so children can gate by it
        setLiqCfg({ ...liq, ...sonic });
        setProfitCfg(prof);
        setMarketCfg(mkt);
        setPctMoves(moves);
        setLoopSec(loop);
        setNearestLiq(nearest);
        setDirty(false);
      } catch (e) {
        // best-effort; page still renders
      }
    })();
    return () => {
      // Leaving Monitor Manager: force dashboards to refresh next paint
      alive = false;
      try {
        // These helpers handle their own SWR keys; monitorStatus needs an explicit mutate
        refreshActiveSession();
        refreshLatestPortfolio();
        mutate(statusEP.summary, undefined, { revalidate: true });
      } catch {}
    };
  }, []);

  const handleSaveAll = useCallback(async () => {
    setSaving(true);
    try {
      const sonicPatch = {
        interval_seconds: Number.isFinite(Number(loopSec)) ? Number(loopSec) : undefined,
        enabled_sonic: liqCfg?.enabled_sonic
      };
      // Market endpoint is retired in refreshed core; ignore 410 Gone if present.
      const postMarket = axios
        .post('/api/monitor-settings/market', marketCfg)
        .catch((err) => {
          if (err?.response?.status !== 410) throw err;
        });
      const liqPatch = {};
      if (liqCfg?.thresholds) liqPatch.thresholds = liqCfg.thresholds;
      if (liqCfg?.blast_radius) liqPatch.blast_radius = liqCfg.blast_radius;
      if (liqCfg?.notifications) liqPatch.notifications = liqCfg.notifications;
      if (liqCfg?.snooze_seconds != null) liqPatch.snooze_seconds = liqCfg.snooze_seconds;

      await Promise.all([
        patchLiquidationSettings(liqPatch),
        postMarket,
        // prefer helper if present
        (saveProfitCfg ? saveProfitCfg(profitCfg) : axios.post('/api/monitor-settings/profit', profitCfg)),
        axios.post('/api/monitor-settings/sonic', sonicPatch)
      ]);
      setDirty(false);
      setToast({ open: true, msg: 'Monitor settings saved', sev: 'success' });
    } catch (err) {
      setToast({ open: true, msg: 'Save failed: ' + (err?.message || 'unknown error'), sev: 'error' });
    } finally {
      setSaving(false);
    }
  }, [liqCfg, marketCfg, profitCfg, loopSec, saveProfitCfg]);

  const isSonicOn = Boolean(liqCfg?.enabled_sonic ?? true);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Header with Save All on right */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h3" fontWeight={700}>Monitor Manager</Typography>
        <Button
          variant="contained"
          disabled={!dirty || saving}
          onClick={handleSaveAll}
        >
          {saving ? 'Saving…' : 'Save All'}
        </Button>
      </Box>

      {/* 2x2 grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: `${COLUMN_A_WIDTH}px 1fr`,
          gridAutoRows: 'minmax(320px, auto)',
          gap: `${GRID_GAP}px`
        }}
      >
        {/* Sonic master (always interactive) */}
        <SonicMonitorCard
          cfg={liqCfg}
          setCfg={setLiqCfgDirty}
          loop={loopSec}
          setLoop={setLoopSecDirty}
        />

        {/* Liquidation */}
        <LiquidationMonitorCard
          cfg={liqCfg}
          setCfg={setLiqCfgDirty}
          blast={liqCfg?.blast_radius || {}}
          nearest={nearestLiq}
          disabled={!isSonicOn}
        />

        {/* Profit */}
        <ProfitMonitorCard
          cfg={profitCfg}
          setCfg={setProfitCfgDirty}
          disabled={!isSonicOn}
        />

        {/* Market */}
        <MarketMonitorCard
          cfg={marketCfg}
          setCfg={setMarketCfgDirty}
          live={pctMoves}
          disabled={!isSonicOn}
        />
      </Box>

      <Snackbar
        open={toast.open}
        autoHideDuration={3500}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
      >
        <Alert onClose={() => setToast((t) => ({ ...t, open: false }))} severity={toast.sev} sx={{ width: '100%' }}>
          {toast.msg}
        </Alert>
      </Snackbar>
    </Box>
  );
}

