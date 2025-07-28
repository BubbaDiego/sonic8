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
  Stack,
  CircularProgress,
  Switch,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from '@mui/material';
import Paper from '@mui/material/Paper';

import WaterDropIcon from '@mui/icons-material/WaterDrop';
import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import BlurCircularTwoToneIcon from '@mui/icons-material/BlurCircularTwoTone'; // 💥 BR
import TuneTwoToneIcon from '@mui/icons-material/TuneTwoTone';                 // Threshold hdr
import InsightsTwoToneIcon from '@mui/icons-material/InsightsTwoTone';         // Current hdr

// NEW colorful icons for notification-state indicators
import MemoryIcon from '@mui/icons-material/Memory';              // System
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver'; // Voice
import SmsIcon from '@mui/icons-material/Sms';                    // SMS
import CampaignIcon from '@mui/icons-material/Campaign';          // TTS

// use asset logos instead of MUI icons
import btcLogo from '/images/btc_logo.png';
import ethLogo from '/images/eth_logo.png';
import solLogo from '/images/sol_logo.png';

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

function NotificationBar({ cfg, toggle }) {
  const items = [
    { key: 'system', label: 'System', icon: MemoryIcon, color: 'info' },
    { key: 'voice', label: 'Voice', icon: RecordVoiceOverIcon, color: 'success' },
    { key: 'sms', label: 'SMS', icon: SmsIcon, color: 'warning' },
    { key: 'tts', label: 'TTS', icon: CampaignIcon, color: 'error' }
  ];

  return (
    <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
      <Paper variant="outlined" sx={{ px: 2, py: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
        <Stack direction="row" spacing={3}>
          {items.map(({ key, label, icon: Icon, color }) => (
            <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <ToggleButton
                size="small"
                value={key}
                selected={cfg[key]}
                onChange={() => toggle(key)}
                sx={{ width: 60, height: 28, fontSize: 11, p: 0 }}
              >
                {label}
              </ToggleButton>
              <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
            </Box>
          ))}
        </Stack>
      </Paper>
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


  const getNearestObj = (code) => {
    const v = nearest[code];
    if (v == null) return { dist: "\u2014", side: "" };
    if (typeof v === "number") return { dist: v, side: "" };
    return { dist: v.dist, side: v.side };
  };

  const getDistColour = (code) => {
    const br = normCfg.blast_radius[code];
    const d = getNearestObj(code).dist;
    if (typeof d !== "number" || typeof br !== "number") return "text.primary";
    if (d > br) return "success.main";
    if (d > br * 0.5) return "warning.main";
    return "error.main";
  };

  return (
    <Card variant="outlined" sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600}>Liquidation Monitor</Typography>
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
        {/* New compact table -------------------------------------------------- */}
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <TuneTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>Threshold</Typography>
                </Stack>
              </TableCell>
              <TableCell>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <InsightsTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>Current</Typography>
                </Stack>
              </TableCell>
              <TableCell align="center">
                <Stack direction="row" spacing={0.5} justifyContent="center">
                  <BlurCircularTwoToneIcon fontSize="inherit" />
                  <Typography variant="subtitle2" fontWeight={700}>Blast Radius</Typography>
                </Stack>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {ASSETS.map(({ code, icon }) => {
              const { dist } = getNearestObj(code);
              return (
                <TableRow key={code}>
                  {/* icon + threshold share ONE cell */}
                  <TableCell sx={{ width: 160 }}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <img src={icon} width={22} alt={code} style={{ flexShrink: 0 }} />
                      <TextField
                        type="number"
                        size="small"
                        value={normCfg.thresholds[code]}
                        onChange={handleThresholdChange(code)}
                        sx={{ width: 110 }}
                      />
                    </Stack>
                  </TableCell>

                  {/* current distance (icon removed) */}
                  <TableCell align="center" sx={{ width: 140, color: getDistColour(code) }}>
                    <Typography variant="body2" sx={{ textAlign: 'center' }}>
                      {dist}
                    </Typography>
                  </TableCell>

                  {/* blast-radius button */}
                  <TableCell align="center" sx={{ width: 100 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      sx={{ minWidth: 70 }}
                      onClick={applyBlast(code)}
                    >
                      {normCfg.blast_radius[code]?.toFixed(1) || '—'}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        <NotificationBar
          cfg={normCfg.notifications}
          toggle={(k) =>
            setCfg(prev => ({
              ...prev,
              notifications: { ...prev.notifications, [k]: !prev.notifications[k] }
            }))
          }
        />
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
            <Typography variant="h4" fontWeight={600}>Global Settings</Typography>
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
                    <img src="/images/hedgehog_icon.png" width={16} alt="Loop" />
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
                    <img src="/images/zzz_icon.png" width={16} alt="Zzz" />
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
      enabled: cfg.enabled ?? true,
      notifications: { system: true, voice: true, sms: false, tts: true, ...(cfg.notifications || {}) },
      ...cfg
    }),
    [cfg]
  );

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCfg((prev) => ({ ...prev, [name]: value }));
  };

  const handleEnabledChange = (e) =>
    setCfg((prev) => ({ ...prev, enabled: e.target.checked }));


  return (
    <Card variant="outlined" sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={600}>Profit Monitor</Typography>
            <TrendingUpTwoToneIcon fontSize="small" />
          </Stack>
        }
        action={
          <Tooltip title={normCfg.enabled ? 'Monitor enabled' : 'Monitor disabled'}>
            <Switch size="small" checked={normCfg.enabled} onChange={handleEnabledChange} />
          </Tooltip>
        }
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

        <NotificationBar
          cfg={normCfg.notifications}
          toggle={(k) =>
            setCfg(prev => ({
              ...prev,
              notifications: { ...prev.notifications, [k]: !prev.notifications[k] }
            }))
          }
        />
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