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
  Stack,
  CircularProgress,
  Switch,
  Tooltip
} from '@mui/material';

import WaterDropIcon from '@mui/icons-material/WaterDrop';

// use asset logos instead of MUI icons
import btcLogo from '/static/images/btc_logo.png';
import ethLogo from '/static/images/eth_logo.png';
import solLogo from '/static/images/sol_logo.png';

// ─────────────────────────────────────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────────────────────────────────────
const ASSETS = [
  { code: 'BTC', icon: btcLogo },
  { code: 'ETH', icon: ethLogo },
  { code: 'SOL', icon: solLogo }
];

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────────────────
function CircularCountdown({ remaining, total }) {
  const pct = (remaining / total) * 100;
  return (
    <Box sx={{ position: 'relative', display: 'inline-flex' }}>
      <CircularProgress value={pct} variant="determinate" size={80} thickness={4} />
      <Box
        sx={{
          top: 0,
          left: 0,
          bottom: 0,
          right: 0,
          position: 'absolute',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Typography variant="h6" component="div" color="text.secondary">
          {remaining}s
        </Typography>
      </Box>
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Left‑hand card – per‑asset thresholds + notifications
// ─────────────────────────────────────────────────────────────────────────────
function AssetThresholdCard({ cfg, setCfg, blast, nearest = {} }) {
  const normCfg = useMemo(
    () => ({
      thresholds: { BTC: '', ETH: '', SOL: '', ...(cfg.thresholds || {}) },
      blast_radius: blast || {},
      notifications: { system: true, voice: true, sms: false, tts: true, ...(cfg.notifications || {}) },
      enabled: cfg.enabled ?? true
    }),
    [cfg, blast]
  );

  const handleThresholdChange = (asset) => (e) => {
    setCfg((prev) => ({
      ...prev,
      thresholds: { ...(prev.thresholds || {}), [asset]: e.target.value }
    }));
  };

  // ── master enable/disable ──────────────────────────────────────────────
  const handleEnabledChange = (e) => {
    setCfg((prev) => ({ ...prev, enabled: e.target.checked }));
  };

  const applyBlast = (asset) => () => {
    const br = normCfg.blast_radius[asset];
    setCfg((prev) => ({
      ...prev,
      thresholds: { ...(prev.thresholds || {}), [asset]: br }
    }));
  };

  const handleNotifChange = (_, selections) => {
    setCfg((prev) => ({
      ...prev,
      notifications: {
        system: selections.includes('system'),
        voice: selections.includes('voice'),
        sms: selections.includes('sms'),
        tts: selections.includes('tts')
      }
    }));
  };

  const selectedNotifs = Object.entries(normCfg.notifications)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <Card variant="outlined">
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6">Liquidation Monitor</Typography>
            <WaterDropIcon fontSize="small" color="primary" />
          </Stack>
        }
        action={
          <Tooltip title={normCfg.enabled ? 'Monitor enabled' : 'Monitor disabled'}>
            <Switch size="small" checked={normCfg.enabled} onChange={handleEnabledChange} />
          </Tooltip>
        }
      />
      <CardContent>
        {ASSETS.map(({ code, icon }) => (
          <Stack key={code} direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <img src={icon} width={20} alt={code} />
            <TextField
              label={`${code} Threshold`}
              type="number"
              size="small"
              value={normCfg.thresholds[code]}
              onChange={handleThresholdChange(code)}
              sx={{ width: 110 }}
            />
            <Button variant="outlined" size="small" sx={{ minWidth: 48 }} onClick={applyBlast(code)}>
              {normCfg.blast_radius[code]?.toFixed(1) || '—'}
            </Button>

            {/* widened nearest‑distance box */}
            <TextField
              value={nearest[code] ?? '—'}
              size="small"
              inputProps={{ readOnly: true }}
              sx={{ width: 120 }}
            />
          </Stack>
        ))}

        <Typography variant="subtitle2" sx={{ mt: 2 }}>
          Notifications
        </Typography>
        <ToggleButtonGroup size="small" value={selectedNotifs} onChange={handleNotifChange} aria-label="notification types">
          <ToggleButton value="system">System</ToggleButton>
          <ToggleButton value="voice">Voice</ToggleButton>
          <ToggleButton value="sms">SMS</ToggleButton>
          <ToggleButton value="tts">TTS</ToggleButton>
        </ToggleButtonGroup>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Right‑hand card – global threshold %, snooze, start‑snooze button
// ─────────────────────────────────────────────────────────────────────────────
function GlobalSnoozeCard({ cfg, setCfg, loop, setLoop }) {
  const [remaining, setRemaining] = useState(0);
  const [running, setRunning] = useState(false);

  const thresh = cfg.threshold_percent ?? '';
  const snooze = cfg.snooze_seconds ?? '';
  const loopSec = loop ?? '';

  // start countdown
  const start = () => {
    const sec = parseInt(snooze, 10);
    if (sec > 0) {
      setRemaining(sec);
      setRunning(true);
    }
  };

  // ticking effect
  React.useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          setRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setCfg((prev) => ({ ...prev, [name]: value }));
  };

  const onLoopChange = (e) => setLoop(e.target.value);

  return (
    <Card variant="outlined">
      <CardHeader title="Global Threshold & Snooze" />
      <CardContent>
        <Stack spacing={2}>
          <TextField
            label="Threshold %"
            type="number"
            name="threshold_percent"
            value={thresh}
            onChange={onChange}
            inputProps={{ step: '0.1' }}
          />
          <TextField label="Sonic Loop (seconds)" type="number" value={loopSec} onChange={onLoopChange} />
          <TextField label="Snooze (seconds)" type="number" name="snooze_seconds" value={snooze} onChange={onChange} />

          {running ? (
            <CircularCountdown remaining={remaining} total={snooze || 1} />
          ) : (
            <Button variant="outlined" onClick={start}>
              Start Snooze Countdown
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Profit Monitor card (unchanged)
// ─────────────────────────────────────────────────────────────────────────────
function ProfitSettings({ cfg, setCfg }) {
  const normCfg = useMemo(
    () => ({
      notifications: { system: true, voice: true, sms: false, tts: true, ...(cfg.notifications || {}) },
      ...cfg
    }),
    [cfg]
  );

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCfg((prev) => ({ ...prev, [name]: value }));
  };

  const handleNotifChange = (_, selections) => {
    setCfg((prev) => ({
      ...prev,
      notifications: {
        system: selections.includes('system'),
        voice: selections.includes('voice'),
        sms: selections.includes('sms'),
        tts: selections.includes('tts')
      }
    }));
  };

  const selectedNotifs = Object.entries(normCfg.notifications)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <Card variant="outlined">
      <CardHeader title="Profit Monitor" subheader="Single & portfolio profit thresholds" />
      <CardContent>
        <Stack spacing={2}>
          {['single_high', 'portfolio_high', 'single_low', 'portfolio_low'].map((field) => (
            <TextField
              key={field}
              fullWidth
              label={`${field.replace('_', ' ').toUpperCase()} ($)`}
              name={field}
              type="number"
              value={normCfg[field] ?? ''}
              onChange={handleChange}
            />
          ))}
        </Stack>

        <Typography variant="subtitle2" sx={{ mt: 2 }}>
          Notifications
        </Typography>
        <ToggleButtonGroup size="small" value={selectedNotifs} onChange={handleNotifChange} aria-label="notification types">
          <ToggleButton value="system">System</ToggleButton>
          <ToggleButton value="voice">Voice</ToggleButton>
          <ToggleButton value="sms">SMS</ToggleButton>
          <ToggleButton value="tts">TTS</ToggleButton>
        </ToggleButtonGroup>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Main page component
// ─────────────────────────────────────────────────────────────────────────────
export default function MonitorManager() {
  const [liqCfg, setLiqCfg] = useState({});
  const [profitCfg, setProfitCfg] = useState({});
  const [marketCfg, setMarketCfg] = useState({});
  const [loopSec, setLoopSec] = useState('');
  const [nearestLiq, setNearestLiq] = useState({});
  const [toast, setToast] = useState('');

  // initial fetch
  useEffect(() => {
    axios.get('/api/monitor-settings/liquidation').then((r) => setLiqCfg(r.data));
    axios.get('/api/monitor-settings/profit').then((r) => setProfitCfg(r.data));
    axios.get('/api/monitor-settings/market').then((r) => setMarketCfg(r.data));
    axios.get('/api/monitor-settings/sonic').then((r) => {
      setLoopSec(String(r.data.interval_seconds ?? ''));
    });

    axios
      .get('/api/liquidation/nearest-distance')
      .then((r) => setNearestLiq(r.data))
      .catch(() => setNearestLiq({}));
  }, []);

  // Blast radius buttons would be rendered next to each asset threshold
  // Example: <Button onClick={() => setLiqCfg(prev=>({...prev, thresholds:{...prev.thresholds, BTC: marketCfg.blast_radius?.BTC}}))}>BR</Button>

  const saveAll = async () => {
    await axios.post('/api/monitor-settings/liquidation', liqCfg);
    await axios.post('/api/monitor-settings/profit', profitCfg);
    await axios.post('/api/monitor-settings/market', marketCfg);
    await axios.post('/api/monitor-settings/sonic', { interval_seconds: parseInt(loopSec || '0', 10) });
    setToast('Settings saved');
  };

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Monitor Manager
      </Typography>

      <Grid container spacing={3}>
        {/* Liquidation monitor section split in two cards */}
        <Grid item xs={12} md={6}>
          <AssetThresholdCard cfg={liqCfg} setCfg={setLiqCfg} blast={marketCfg.blast_radius} nearest={nearestLiq} />
        </Grid>
        <Grid item xs={12} md={6}>
          <GlobalSnoozeCard cfg={liqCfg} setCfg={setLiqCfg} loop={loopSec} setLoop={setLoopSec} />
        </Grid>

        {/* Profit monitor */}
        <Grid item xs={12}>
          <ProfitSettings cfg={profitCfg} setCfg={setProfitCfg} />
        </Grid>

        {/* Save button */}
        <Grid item xs={12}>
          <Button variant="contained" onClick={saveAll}>
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
        <Alert severity="success">{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
