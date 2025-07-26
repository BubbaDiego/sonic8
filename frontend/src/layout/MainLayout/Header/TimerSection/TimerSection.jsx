// TimerSection.jsx – radial countdowns for Sonic monitor and Liquidation snooze
import { useEffect, useState } from 'react';
import { CircularProgress, Tooltip, Box } from '@mui/material';
import axios from 'utils/axios';

const FULL_SONIC  = 3600; // 60 minutes
const FULL_SNOOZE = 600;  // 10 minutes
const POLL_MS     = 5000; // refresh every 5 s

function RadialTimer({ seconds, total, label, color }) {
  const pct = Math.min(100, (seconds / total) * 100);
  return (
    <Tooltip title={`${label}: ${seconds}s`} arrow>
      <Box sx={{ position: 'relative', display: 'inline-flex', mx: 1 }}>
        <CircularProgress
          variant="determinate"
          value={pct}
          size={38}
          thickness={4}
          color={color}
          sx={{ transition: 'stroke-dashoffset 0.1s linear' }}
        />
        <Box
          sx={{
            top: 0, left: 0, bottom: 0, right: 0,
            position: 'absolute',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.65rem',
            pointerEvents: 'none'
          }}
        >
          {Math.floor(seconds)}
        </Box>
      </Box>
    </Tooltip>
  );
}

export default function TimerSection() {
  const [sonic, setSonic] = useState(0);
  const [snooze, setSnooze] = useState(0);
  const [sonicNextTs, setSonicNextTs] = useState(Date.now());
  const [snoozeEndTs, setSnoozeEndTs] = useState(Date.now());

useEffect(() => {
  let timeoutHandle;
  const poll = async () => {
    try {
      const { data } = await axios.get('/api/monitor-status/');
      const now = Date.now();
      setSonicNextTs(now + (data?.sonic_next ?? 0) * 1000);
      setSnoozeEndTs(now + (data?.liquid_snooze ?? 0) * 1000);
    } catch (err) {
      // Log the error so failed requests are visible during debugging
      console.error('Failed to fetch monitor status:', err);
    }
    timeoutHandle = setTimeout(poll, POLL_MS);
  };
  poll();
  return () => {
    clearTimeout(timeoutHandle);
  };
}, []);

useEffect(() => {
  let frameId;
  const tick = () => {
    setSonic(Math.max(0, (sonicNextTs - Date.now()) / 1000));
    setSnooze(Math.max(0, (snoozeEndTs - Date.now()) / 1000));
    frameId = requestAnimationFrame(tick);
  };
  frameId = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(frameId);
}, [sonicNextTs, snoozeEndTs]);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', mx: 1 }}>
      <RadialTimer seconds={sonic}  total={FULL_SONIC}  label="Next Sonic" color="success" />
      <RadialTimer seconds={snooze} total={FULL_SNOOZE} label="Liq Snooze" color="warning" />
    </Box>
  );
}
