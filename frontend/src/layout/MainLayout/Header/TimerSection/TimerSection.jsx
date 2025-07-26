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
  const [sonic, setSonic]     = useState(0);
  const [snooze, setSnooze]   = useState(0);

useEffect(() => {
  let timeoutHandle;
  let intervalId;
  const poll = async () => {
    try {
      const { data } = await axios.get('/api/monitor-status/');
      setSonic(Math.max(0, Math.floor(data?.sonic_next    ?? 0)));
      setSnooze(Math.max(0, Math.floor(data?.liquid_snooze ?? 0)));
    } catch (err) {
      // Log the error so failed requests are visible during debugging
      console.error('Failed to fetch monitor status:', err);
    }
    timeoutHandle = setTimeout(poll, POLL_MS);
  };
  poll();
  intervalId = setInterval(() => {
    setSonic(prev => Math.max(0, prev - 1));
    setSnooze(prev => Math.max(0, prev - 1));
  }, 1000);
  return () => {
    clearTimeout(timeoutHandle);
    clearInterval(intervalId);
  };
}, []);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', mx: 1 }}>
      <RadialTimer seconds={sonic}  total={FULL_SONIC}  label="Next Sonic" color="success" />
      <RadialTimer seconds={snooze} total={FULL_SNOOZE} label="Liq Snooze" color="warning" />
    </Box>
  );
}
