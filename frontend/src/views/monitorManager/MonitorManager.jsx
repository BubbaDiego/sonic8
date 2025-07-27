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
import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';

// NEW colorful icons for notification-state indicators
import MemoryIcon from '@mui/icons-material/Memory';              // System
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver'; // Voice
import SmsIcon from '@mui/icons-material/Sms';                    // SMS
import CampaignIcon from '@mui/icons-material/Campaign';          // TTS

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

  const getNearestObj = (code) => {
    const v = nearest[code];
    if (v == null) return { dist: "\u2014", side: "" };
    if (typeof v === "number") return { dist: v, side: "" };
    return { dist: v.dist, side: v.side };
  };

  return (
    <Card variant="outlined" sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h5">Liquidation Monitor</Typography>
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

            {/* nearest distance + side */}
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography
                variant="caption"
                sx={{ width: 42, textAlign: 'right' }}
              >
                {getNearestObj(code).side}
              </Typography>
              <TextField
                value={getNearestObj(code).dist}
                size="small"
                inputProps={{ readOnly: true }}
                sx={{ width: 88 }}
              />
            </Stack>
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

        {/* Visual indicator icons */}
        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
          {normCfg.notifications.system && <MemoryIcon color="info" fontSize="small" />}
          {normCfg.notifications.voice && <RecordVoiceOverIcon color="success" fontSize="small" />}
          {normCfg.notifications.sms && <SmsIcon color="warning" fontSize="small" />}
          {normCfg.notifications.tts && <CampaignIcon color="error" fontSize="small" />}
        </Stack>
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
    <Card variant="outlined" sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6">Global Settings</Typography>
            <SettingsTwoToneIcon fontSize="small" />
          </Stack>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>Sonic Loop</Typography>
                    <img src="/static/images/hedgehog_icon.png" width={16} alt="Loop" />
                  </Stack>
                }
                type="number"
                value={loopSec}
                onChange={onLoopChange}
              />
              <TextField
                label="Threshold %"
                type="number"
                name="threshold_percent"
                value={thresh}
                onChange={onChange}
                inputProps={{ step: '0.1' }}
              />
            </Stack>
          </Grid>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>Snooze</Typography>
                    <img src="/static/images/zzz_icon.png" width={16} alt="Zzz" />
                  </Stack>
                }
                type="number"
                name="snooze_seconds"
                value={snooze}
                onChange={onChange}
              />
              {running ? (
                <CircularCountdown remaining={remaining} total={snooze || 1} />
              ) : (
                <Button variant="outlined" onClick={start}>
                  Start Snooze Countdown
                </Button>
              )}
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Profit Monitor card
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
    <Card variant="outlined" sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h5">Profit Monitor</Typography>
            <TrendingUpTwoToneIcon fontSize="small" />
          </Stack>
        }
        subheader="Single & portfolio profit thresholds"
      />
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                fullWidth
                label="PORTFOLIO HIGH ($)"
                name="portfolio_high"
                type="number"
                value={normCfg.portfolio_high ?? ''}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="PORTFOLIO LOW ($)"
                name="portfolio_low"
                type="number"
                value={normCfg.portfolio_low ?? ''}
                onChange={handleChange}
              />
            </Stack>
          </Grid>
          <Grid item xs={6}>
            <Stack spacing={2}>
              <TextField
                fullWidth
                label="SINGLE HIGH ($)"
                name="single_high"
                type="number"
                value={normCfg.single_high ?? ''}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="SINGLE LOW ($)"
                name="single_low"
                type="number"
                value={normCfg.single_low ?? ''}
                onChange={handleChange}
              />
            </Stack>
          </Grid>
        </Grid>

        <Typography variant="subtitle2" sx={{ mt: 2 }}>
          Notifications
        </Typography>
        <ToggleButtonGroup size="small" value={selectedNotifs} onChange={handleNotifChange} aria-label="notification types">
          <ToggleButton value="system">System</ToggleButton>
          <ToggleButton value="voice">Voice</ToggleButton>
          <ToggleButton value="sms">SMS</ToggleButton>
          <ToggleButton value="tts">TTS</ToggleButton>
        </ToggleButtonGroup>

        {/* Visual indicator icons */}
        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
          {normCfg.notifications.system && <MemoryIcon color="info" fontSize="small" />}
          {normCfg.notifications.voice && <RecordVoiceOverIcon color="success" fontSize="small" />}
          {normCfg.notifications.sms && <SmsIcon color="warning" fontSize="small" />}
          {normCfg.notifications.tts && <CampaignIcon color="error" fontSize="small" />}
        </Stack>
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
        {/* Row 1: Liquidation + Profit monitor side by side */}
        <Grid item xs={12} md={6}>
          <AssetThresholdCard cfg={liqCfg} setCfg={setLiqCfg} blast={marketCfg.blast_radius} nearest={nearestLiq} />
        </Grid>
        <Grid item xs={12} md={6}>
          <ProfitSettings cfg={profitCfg} setCfg={setProfitCfg} />
        </Grid>

        {/* Row 2: Global snooze settings */}
        <Grid item xs={12}>
          <GlobalSnoozeCard cfg={liqCfg} setCfg={setLiqCfg} loop={loopSec} setLoop={setLoopSec} />
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