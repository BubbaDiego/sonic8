import { useEffect, useState, useCallback, useRef } from 'react';
import { Box, Stack, Popover, Typography, Button, Tooltip, IconButton } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import DonutCountdown from './DonutCountdown';
import axios from 'utils/axios';
import {
  refreshLatestPortfolio,
  refreshPortfolioHistory,
} from 'api/portfolio';
import { refreshPositions } from 'api/positions';
import { refreshMonitorStatus } from 'api/monitorStatus';
import { IconShieldCheck, IconShieldOff } from '@tabler/icons-react';

const FULL_SONIC = 3600; // 60 min
const DEFAULT_SNOOZE = 600; // 10 min fallback

const POLL_MS = 5000;
const SONIC_REFRESH_DELAY_MS = 5000;

export default function TimerSection() {
  const theme = useTheme();
  const [sonic, setSonic] = useState(0);
  const [snooze, setSnooze] = useState(0);
  const [sonicNextTs, setSonicNextTs] = useState(Date.now());
  const [snoozeEndTs, setSnoozeEndTs] = useState(Date.now());
  const [fullSnooze, setFullSnooze] = useState(DEFAULT_SNOOZE);

  const [sonicActive, setSonicActive] = useState(false);

  const [anchorEl, setAnchorEl] = useState(null);
  const [activeLabel, setActiveLabel] = useState('');

  const [lastSonicComplete, setLastSonicComplete] = useState(null);

  // Track the last sonic completion timestamp we've seen
  const lastSonicCompleteRef = useRef(null);

  const openPopover = Boolean(anchorEl);

  // ---------------- Fetch snooze duration once on mount ---------------
  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get('/api/monitor-settings/liquidation');
        setFullSnooze(data?.snooze_seconds ?? DEFAULT_SNOOZE);
      } catch (err) {
        console.error('Failed to fetch liquidation settings:', err);
      }
    })();
  }, []);

  // ---------------- Poll backend for fresh timestamps -----------------
  useEffect(() => {
    let id;
    const poll = async () => {
      try {
        const { data } = await axios.get('/api/monitor-status/');
        const now = Date.now();
        setSonicNextTs(now + (data?.sonic_next ?? 0) * 1000);
        setSnoozeEndTs(now + (data?.liquid_snooze ?? 0) * 1000);
        const sonicStatus = data?.monitors?.['Sonic Monitoring']?.status;
        setSonicActive(sonicStatus === 'Healthy');

        // Detect Sonic completion and trigger refresh if changed
        const lastComplete = data?.sonic_last_complete ?? null;
        setLastSonicComplete(lastComplete);
        if (lastSonicCompleteRef.current === null) {
          lastSonicCompleteRef.current = lastComplete;
        } else if (lastComplete && lastComplete !== lastSonicCompleteRef.current) {
          lastSonicCompleteRef.current = lastComplete;
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
          refreshMonitorStatus();
        }
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
    } else if (activeLabel === 'Snooze') {
      // Could expose explicit API; for now just refresh monitor
      refreshMonitorStatus();
    }
  };

  const sonicTooltip = lastSonicComplete
    ? `Last update: ${new Date(lastSonicComplete).toLocaleString()}`
    : 'Last update: never';

  const showShield = snooze <= 0 && sonicActive;

  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mx: 1 }}>
        <DonutCountdown
          remaining={sonic}
          total={FULL_SONIC}
          label="Next Sonic"
          paletteKey="success"
          onClick={handleDonutClick('Next Sonic')}
          tooltip={sonicTooltip}
        />
        {snooze > 0 ? (
          <DonutCountdown
            remaining={snooze}
            total={fullSnooze}
            label="Snooze"
            paletteKey="warning"
            onClick={handleDonutClick('Snooze')}
          />
        ) : (
          <Tooltip
            title=
              {showShield
                ? 'Liquidation protection active'
                : 'Sonic monitor inactive – no liquidation protection'}
            arrow
          >
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <IconButton
                aria-label="Snooze status"
                onClick={handleDonutClick('Snooze')}
                sx={{ p: 0, width: 48, height: 48 }}
                disableRipple
              >
                {showShield ? (
                  <IconShieldCheck size={48} color={theme.palette.success.main} />
                ) : (
                  <IconShieldOff size={48} color={theme.palette.error.main} />
                )}
              </IconButton>
            </Box>
          </Tooltip>
        )}
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
              : `Liquidation snooze prevents repeat notifications for ${Math.round(
                  fullSnooze / 60
                )} min. Click below to clear the snooze.`}
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
