import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CardContent,
  TextField,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Typography,
  Stack,
  Box,
  Chip,
  Tooltip,
  Divider
} from '@mui/material';

import WaterDropIcon from '@mui/icons-material/WaterDrop';
import TuneTwoToneIcon from '@mui/icons-material/TuneTwoTone';
import InsightsTwoToneIcon from '@mui/icons-material/InsightsTwoTone';
import BlurCircularTwoToneIcon from '@mui/icons-material/BlurCircularTwoTone';

import MonitorUpdateBar from './MonitorUpdateBar';
import MiniStepper from 'components/MiniStepper';
import MainCard from 'ui-component/cards/MainCard';

import btcLogo from 'images/btc_logo.png';
import ethLogo from 'images/eth_logo.png';
import solLogo from 'images/sol_logo.png';

const ASSETS = [
  { code: 'BTC', icon: btcLogo },
  { code: 'ETH', icon: ethLogo },
  { code: 'SOL', icon: solLogo }
];

export default function LiquidationMonitorCard({ cfg, setCfg, blast = {}, nearest = {}, disabled = false }) {
  const [draft, setDraft] = useState(cfg || {});

  const normalise = useCallback((v, fb = 0) => {
    if (v == null || v === '') return fb;
    const n = Number(String(v).replace(/,/g, ''));
    return Number.isFinite(n) ? Math.round(n * 100) / 100 : fb;
  }, []);

  const fallbackBlast = useMemo(
    () => ({
      BTC: normalise(blast?.BTC ?? 0),
      ETH: normalise(blast?.ETH ?? 0),
      SOL: normalise(blast?.SOL ?? 0)
    }),
    [blast, normalise]
  );

  useEffect(() => {
    setDraft((prev) => {
      const next = { ...(cfg || {}) };
      const r = cfg?.blast_radius || {};
      next.blast_radius = {
        BTC: normalise(r.BTC ?? prev?.blast_radius?.BTC ?? fallbackBlast.BTC, fallbackBlast.BTC),
        ETH: normalise(r.ETH ?? prev?.blast_radius?.ETH ?? fallbackBlast.ETH, fallbackBlast.ETH),
        SOL: normalise(r.SOL ?? prev?.blast_radius?.SOL ?? fallbackBlast.SOL, fallbackBlast.SOL)
      };
      return next;
    });
  }, [cfg, fallbackBlast, normalise]);

  const normCfg = useMemo(
    () => ({
      thresholds: { BTC: '', ETH: '', SOL: '', ...(draft?.thresholds || {}) },
      blast_radius: {
        BTC: normalise(draft?.blast_radius?.BTC ?? fallbackBlast.BTC, fallbackBlast.BTC),
        ETH: normalise(draft?.blast_radius?.ETH ?? fallbackBlast.ETH, fallbackBlast.ETH),
        SOL: normalise(draft?.blast_radius?.SOL ?? fallbackBlast.SOL, fallbackBlast.SOL)
      },
      notifications: {
        system: true,
        voice: true,
        sms: false,
        tts: true,
        ...(draft?.notifications || {})
      }
    }),
    [draft, fallbackBlast, normalise]
  );

  const handleThresholdChange = (asset) => (e) => {
    const value = e.target.value;
    setDraft((prev) => ({
      ...prev,
      thresholds: { ...(prev?.thresholds || {}), [asset]: value }
    }));
    setCfg((prev) => ({
      ...prev,
      thresholds: { ...(prev?.thresholds || {}), [asset]: value }
    }));
  };

  const toggleNotify = useCallback(
    (key) => {
      const flip = (state = {}) => {
        const notifications = { ...(state?.notifications || {}) };
        notifications[key] = !Boolean(notifications[key]);
        return { ...state, notifications };
      };
      setDraft((prev) => flip(prev || {}));
      setCfg((prev) => flip(prev || {}));
    },
    [setCfg]
  );

  const getNearestObj = (code) => {
    const v = nearest[code];
    if (v == null) return { dist: '—', side: '' };
    if (typeof v === 'number') return { dist: v, side: '' };
    return { dist: v.dist, side: v.side };
  };

  const refRadius = (code) => {
    const br = normCfg.blast_radius[code];
    const th = Number(normCfg.thresholds[code]);
    return typeof br === 'number' ? br : Number.isFinite(th) ? th : null;
  };
  const distColour = (code) => {
    const d = getNearestObj(code).dist;
    const r = refRadius(code);
    if (typeof d !== 'number' || r == null) return 'text.primary';
    if (d > r) return 'success.main';
    if (d > r * 0.5) return 'warning.main';
    return 'error.main';
  };
  const fmtDistance = (code, val) => {
    if (val == null || val === '—') return val;
    return ['BTC', 'ETH'].includes(code) ? Math.round(val) : code === 'SOL' ? Number(val).toFixed(2) : val;
  };

  return (
    <MainCard
      border
      content={false}
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h4" fontWeight={600} sx={{ fontSize: '1.1rem' }}>
            Liquidation Monitor
          </Typography>
          <WaterDropIcon fontSize="small" color="primary" />
        </Stack>
      }
      secondary={
        <Tooltip title="Enable/disable via Sonic Monitor">
          <Chip
            size="small"
            label={disabled ? 'Disabled' : 'Enabled'}
            color={disabled ? 'default' : 'success'}
            variant={disabled ? 'outlined' : 'filled'}
          />
        </Tooltip>
      }
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        opacity: disabled ? 0.35 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        transition: 'opacity 0.2s ease',
        borderLeft: '4px solid',
        borderLeftColor: disabled ? 'divider' : 'success.main'
      }}
    >
      <CardContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 140, fontWeight: 600 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <TuneTwoToneIcon fontSize="small" />
                  Asset
                </Stack>
              </TableCell>
              <TableCell sx={{ width: 140, fontWeight: 600 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <InsightsTwoToneIcon fontSize="small" />
                  Current
                </Stack>
              </TableCell>
              <TableCell sx={{ width: 180, fontWeight: 600 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <BlurCircularTwoToneIcon fontSize="small" />
                  Threshold
                </Stack>
              </TableCell>
              <TableCell sx={{ width: 160, fontWeight: 600 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <BlurCircularTwoToneIcon fontSize="small" />
                  Blast Radius
                </Stack>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {ASSETS.map(({ code, icon }) => {
              const nearestObj = getNearestObj(code);
              const radius = refRadius(code);
              const pct =
                typeof nearestObj.dist === 'number' && typeof radius === 'number' && radius > 0
                  ? Math.ceil((nearestObj.dist / radius) * 100)
                  : null;
              return (
                <TableRow key={code}>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <img src={icon} alt={code} style={{ width: 18, height: 18, opacity: 0.9 }} />
                      <Typography variant="body2" fontWeight={600}>{code}</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ color: distColour(code) }}>
                      {fmtDistance(code, nearestObj.dist)} {nearestObj.side ? `(${nearestObj.side})` : ''}
                      {pct != null ? ` • ${pct}%` : ''}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      placeholder="0.00"
                      value={normCfg.thresholds[code]}
                      onChange={handleThresholdChange(code)}
                      inputProps={{
                        inputMode: 'decimal',
                        onWheel: (event) => event.currentTarget.blur()
                      }}
                      sx={{ width: 140 }}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <MiniStepper
                      value={normCfg.blast_radius[code]}
                      onChange={(val) =>
                        setCfg((prev) => ({
                          ...prev,
                          blast_radius: { ...(prev?.blast_radius || {}), [code]: val }
                        }))
                      }
                      step={1}
                      min={0}
                      max={50}
                      label={`Blast radius (${code})`}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
      <Divider sx={{ mx: 2 }} />
      <MonitorUpdateBar
        cfg={normCfg.notifications}
        toggle={toggleNotify}
        sx={{ mx: 2, mb: 2, mt: 1.5 }}
      />
    </MainCard>
  );
}

