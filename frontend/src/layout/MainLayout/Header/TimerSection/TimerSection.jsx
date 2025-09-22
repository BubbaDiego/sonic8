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

import { subscribeToSonicEvents } from 'api/sonicMonitor';

import useSonicStatusPolling from 'hooks/useSonicStatusPolling';

import { IconShieldCheck, IconShieldOff } from '@tabler/icons-react';

const FULL_SONIC = 3600; // 60 min
const DEFAULT_SNOOZE = 600; // 10 min fallback

const SONIC_REFRESH_DELAY_MS = 5000;
const POLL_MS = Number(import.meta.env.VITE_TIMER_POLL_MS ?? 15000);

export default function TimerSection() {
  const theme = useTheme();
  const [sonic, setSonic] = useState(0);
  const [snooze, setSnooze] = useState(0);
  const [fullSnooze, setFullSnooze] = useState(DEFAULT_SNOOZE);

  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const lastSonicCompleteRef = useRef(null);

  const [timerState, setTimerState] = useState({
    sonicNextTs: null,
    snoozeEndTs: null,
    sonicActive: false,
    lastSonicComplete: null
  });

  const {
    sonicNextTs: polledSonicNextTs,
    snoozeEndTs: polledSnoozeEndTs,
    sonicActive: polledSonicActive,
    lastSonicComplete: polledLastSonicComplete
  } = useSonicStatusPolling();

  useEffect(() => {
    setTimerState((prev) => ({
      sonicNextTs: polledSonicNextTs ?? prev.sonicNextTs,
      snoozeEndTs: polledSnoozeEndTs ?? prev.snoozeEndTs,
      sonicActive: polledSonicActive ?? prev.sonicActive,
      lastSonicComplete: polledLastSonicComplete ?? prev.lastSonicComplete
    }));
  }, [polledSonicNextTs, polledSnoozeEndTs, polledSonicActive, polledLastSonicComplete]);

  useEffect(() => {
    async function pollOnce() {
      try {
        const { data } = await axios.get('/api/monitor-status/');
        if (!alive.current) return;
        const now = Date.now();
        const nextState = {
          sonicNextTs: now + (data?.sonic_next ?? 0) * 1000,
          snoozeEndTs: now + (data?.liquid_snooze ?? 0) * 1000,
          sonicActive: data?.monitors?.['Sonic Monitoring']?.status === 'Healthy',
          lastSonicComplete: data?.sonic_last_complete ?? null
        };
        setTimerState((prev) => ({ ...prev, ...nextState }));
      } catch (e) {
        console.error('TimerSection poll error:', e);
      }
    }

    pollOnce();
    const id = setInterval(pollOnce, POLL_MS);
    return () => clearInterval(id);
  }, [POLL_MS]);

  useEffect(() => {
    const lastComplete = timerState.lastSonicComplete;
    if (lastComplete == null) {
      lastSonicCompleteRef.current = lastComplete;
      return;
    }

    if (lastSonicCompleteRef.current == null) {
      lastSonicCompleteRef.current = lastComplete;
      return;
    }

    if (lastComplete !== lastSonicCompleteRef.current) {
      lastSonicCompleteRef.current = lastComplete;
      refreshLatestPortfolio();
      refreshPortfolioHistory();
      refreshPositions();
      refreshMonitorStatus();
    }
  }, [timerState.lastSonicComplete]);

  const { sonicNextTs, snoozeEndTs, sonicActive, lastSonicComplete } = timerState;

  const [anchorEl, setAnchorEl] = useState(null);
  const [activeLabel, setActiveLabel] = useState('');

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


  // ---------------- Subscribe to Sonic completion events -------------
  useEffect(() => {
    const es = subscribeToSonicEvents(() => {
      refreshPositions();
      refreshMonitorStatus();
    });
    return () => es.close();
  }, []);

  // ---------------- Poll backend for fresh timestamps -----------------
  // ---------------- Local countdown animation ------------------------
  useEffect(() => {
    let frameId;
    const tick = () => {
      const now = Date.now();
      setSonic(Math.max(0, ((sonicNextTs ?? now) - now) / 1000));
      setSnooze(Math.max(0, ((snoozeEndTs ?? now) - now) / 1000));
      frameId = requestAnimationFrame(tick);
    };
    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [sonicNextTs, snoozeEndTs]);

  // ---------------- Run full refresh once Sonic loop completes -------
  useEffect(() => {
    if (!sonicNextTs) return undefined;
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
