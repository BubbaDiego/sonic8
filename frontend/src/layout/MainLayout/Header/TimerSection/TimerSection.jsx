import { useEffect, useState, useCallback } from 'react';
import { Box, Stack, Popover, Typography, Button } from '@mui/material';
import DonutCountdown from './DonutCountdown';
import axios from 'utils/axios';
import {
  refreshLatestPortfolio,
  refreshPortfolioHistory,
} from 'api/portfolio';
import { refreshPositions } from 'api/positions';
import { refreshMonitorStatus } from 'api/monitorStatus';

const FULL_SONIC = 3600; // 60 min
const FULL_SNOOZE = 600; // 10 min

const POLL_MS = 5000;
const SONIC_REFRESH_DELAY_MS = 5000;

export default function TimerSection() {
  const [sonic, setSonic] = useState(0);
  const [snooze, setSnooze] = useState(0);
  const [sonicNextTs, setSonicNextTs] = useState(Date.now());
  const [snoozeEndTs, setSnoozeEndTs] = useState(Date.now());

  const [anchorEl, setAnchorEl] = useState(null);
  const [activeLabel, setActiveLabel] = useState('');

  const openPopover = Boolean(anchorEl);

  // ---------------- Poll backend for fresh timestamps -----------------
  useEffect(() => {
    let id;
    const poll = async () => {
      try {
        const { data } = await axios.get('/api/monitor-status/');
        const now = Date.now();
        setSonicNextTs(now + (data?.sonic_next ?? 0) * 1000);
        setSnoozeEndTs(now + (data?.liquid_snooze ?? 0) * 1000);
      } catch (err) {
        console.error('Failed to fetch monitor status:', err);
      }
      id = setTimeout(poll, POLL_MS);
    };
    poll();
    return () => clearTimeout(id);
  }, []);

  // ---------------- Local countdown animation ------------------------
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

  // ---------------- Run full refresh once Sonic loop completes -------
  useEffect(() => {
    const delay = Math.max(0, sonicNextTs - Date.now()) + SONIC_REFRESH_DELAY_MS;
    const id = setTimeout(() => {
      refreshLatestPortfolio();
      refreshPortfolioHistory();
      refreshPositions();
      refreshMonitorStatus();
    }, delay);
    return () => clearTimeout(id);
  }, [sonicNextTs]);

  // ---------------- Handlers -----------------------------------------
  const handleDonutClick = useCallback((label) => (event) => {
    setAnchorEl(event.currentTarget);
    setActiveLabel(label);
  }, []);

  const handleClose = () => setAnchorEl(null);

  const handleRunNow = () => {
    handleClose();
    if (activeLabel === 'Next Sonic') {
      refreshLatestPortfolio();
      refreshPortfolioHistory();
      refreshPositions();
      refreshMonitorStatus();
    } else if (activeLabel === 'Liq Snooze') {
      // Could expose explicit API; for now just refresh monitor
      refreshMonitorStatus();
    }
  };

  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mx: 1 }}>
        <DonutCountdown
          remaining={sonic}
          total={FULL_SONIC}
          label="Next Sonic"
          paletteKey="success"
          onClick={handleDonutClick('Next Sonic')}
        />
        <DonutCountdown
          remaining={snooze}
          total={FULL_SNOOZE}
          label="Liq Snooze"
          paletteKey="warning"
          onClick={handleDonutClick('Liq Snooze')}
        />
      </Stack>

      <Popover
        open={openPopover}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Box sx={{ p: 2, maxWidth: 220 }}>
          <Typography variant="subtitle2" gutterBottom>
            {activeLabel}
          </Typography>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            {activeLabel === 'Next Sonic'
              ? 'Sonic monitor scans all active wallets once the timer hits zero. Click below to trigger it now.'
              : 'Liquidation snooze prevents repeat notifications for 10 min. Click below to clear the snooze.'}
          </Typography>
          <Button
            variant="contained"
            size="small"
            fullWidth
            onClick={handleRunNow}
          >
            Run now
          </Button>
        </Box>
      </Popover>
    </>
  );
}
