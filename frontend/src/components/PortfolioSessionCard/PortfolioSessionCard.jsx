import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Card,
  Typography,
  IconButton,
  Box,
  LinearProgress,
  Stack,
  Paper,
  Button,
  TextField
} from '@mui/material';
import { useGetActiveSession } from 'api/session';
import EditIcon from '@mui/icons-material/Edit';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

/* ────────────────────────────────────────────────────────────────────────── */
/*                          ✨  TWEAK‑ME CONFIGS  ✨                          */
/*                                                                           */
/* 1️⃣ CARD_MAX_HEIGHT controls the absolute height of the entire flip card.  */
/*    • Unit: pixels                                                         */
/*    • If you need a taller or shorter widget, bump this number up/down.    */
export const CARD_MAX_HEIGHT = 250; // ← default: 450 px

/* 2️⃣ CARD_CONTENT_TOP_MARGIN is the *inner* top padding for the front &     */
/*    back faces.                                                            */
/*    • Set to 0 for a flush top edge, or raise it for breathing room.       */
export const CARD_CONTENT_TOP_MARGIN = 4; // ← default: 8 px
/* ────────────────────────────────────────────────────────────────────────── */

/* Helper to robustly pull the **current total** regardless of field name */
const pickTotal = (snap) =>
  snap?.current_total_value ??
  snap?.current_total ??
  snap?.current_session_value ?? // legacy field
  snap?.current_value ??
  0;

/* Fallback snapshot for Storybook / offline demos */
const cannedSnapshot = {
  session_start_time: new Date('2025-07-13T13:39:41'),
  current_total_value: 164.41,
  session_performance_value: 0,
  session_start_value: 100,
  session_goal_value: 200
};

export default function PortfolioSessionCard({
  snapshot: snapshotProp,
  onModify,
  onReset
}) {
  /* --------------------------------------------------------------------- */
  /* Live data                                                             */
  /* --------------------------------------------------------------------- */
  const { session } = useGetActiveSession();
  const snapshot = snapshotProp || session || cannedSnapshot;

  /* --------------------------------------------------------------------- */
  /* Local UI state                                                        */
  /* --------------------------------------------------------------------- */
  const [flipped, setFlipped] = useState(false);
  const [editableSnapshot, setEditableSnapshot] = useState({ ...snapshot });

  useEffect(() => {
    setEditableSnapshot({ ...snapshot });
  }, [snapshot]);

  const flipCard = () => setFlipped(!flipped);

  const number = (n) =>
    n?.toLocaleString(undefined, {
      maximumFractionDigits: 2
    });

  /* --------------------------------------------------------------------- */
  /* Derived metrics                                                       */
  /* --------------------------------------------------------------------- */
  const currentTotal = pickTotal(snapshot);

  const perfValue =
    snapshot.session_performance_value
      ? snapshot.session_performance_value
      : currentTotal - snapshot.session_start_value;

  const perfPct = snapshot.session_start_value
    ? (perfValue / snapshot.session_start_value) * 100
    : 0;

  const progress = snapshot.session_goal_value
    ? Math.min(100, (currentTotal / snapshot.session_goal_value) * 100)
    : 0;

  /* --------------------------------------------------------------------- */
  /* Edit‑mode handlers                                                    */
  /* --------------------------------------------------------------------- */
  const handleInputChange = (field, value) => {
    setEditableSnapshot((prev) => {
      const updated = { ...prev };
      if (field === 'session_start_date') {
        const [y, m, d] = value.split('-');
        const t = new Date(updated.session_start_time);
        t.setFullYear(y, m - 1, d);
        updated.session_start_time = t;
      } else if (field === 'session_start_time') {
        const [h, min] = value.split(':');
        const t = new Date(updated.session_start_time);
        t.setHours(h, min);
        updated.session_start_time = t;
      } else {
        updated[field] = parseFloat(value);
      }
      return updated;
    });
  };

  const handleSave = () => {
    onModify?.(editableSnapshot);
    flipCard();
  };

  const sessionDate = snapshot.session_start_time
    ? new Date(snapshot.session_start_time)
    : new Date();

  /* --------------------------------------------------------------------- */
  /* Render                                                                */
  /* --------------------------------------------------------------------- */
  return (
    <Box
      sx={{
        perspective: '1000px',
        height: CARD_MAX_HEIGHT,
        width: '100%'
      }}
    >
      <Box
        sx={{
          width: '100%',
          height: '100%',
          position: 'relative',
          transition: 'transform 0.8s',
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)'
        }}
      >
        {/* FRONT SIDE ----------------------------------------------------- */}
        <Card
          sx={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            pt: CARD_CONTENT_TOP_MARGIN,
            px: 2,
            pb: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'flex-start' // <— content starts at the top
          }}
        >
          <Stack spacing={2} alignItems="center">
            {/* Avatar removed as requested */}

            <Typography variant="h4">{number(currentTotal)} USD</Typography>

            <Typography
              variant="subtitle1"
              color={perfValue >= 0 ? 'success.main' : 'error.main'}
            >
              {perfValue >= 0 ? '+' : ''}
              {number(perfValue)} ({number(perfPct)}%)
            </Typography>

            <Typography variant="subtitle2">
              Goal: {number(snapshot.session_goal_value)} USD
            </Typography>

            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{ width: '100%', borderRadius: 2, height: 8 }}
            />

            {/* Meta row */}
            <Paper
              elevation={3}
              sx={{ p: 1, borderRadius: 2, width: '100%', mt: 1 }}
            >
              <Stack
                direction="row"
                justifyContent="space-around"
                alignItems="center"
              >
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <CalendarTodayIcon fontSize="small" />
                  <Typography variant="caption">
                    {`${sessionDate.getMonth() + 1}/${sessionDate.getDate()}`}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <AccessTimeIcon fontSize="small" />
                  <Typography variant="caption">
                    {sessionDate.toLocaleTimeString([], {
                      hour: 'numeric',
                      minute: '2-digit'
                    })}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <AttachMoneyIcon fontSize="small" />
                  <Typography variant="caption">
                    {number(snapshot.session_start_value)} USD
                  </Typography>
                </Stack>
              </Stack>
            </Paper>

            <IconButton color="primary" onClick={flipCard}>
              <EditIcon />
            </IconButton>
          </Stack>
        </Card>

        {/* BACK SIDE ------------------------------------------------------ */}
        <Card
          sx={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
            pt: CARD_CONTENT_TOP_MARGIN,
            px: 2,
            pb: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'flex-start'
          }}
        >
          <Typography variant="h6">Edit Session</Typography>

          <Stack spacing={1.5} sx={{ mt: 1, width: '90%' }}>
            <TextField
              type="date"
              size="small"
              label="Date"
              InputLabelProps={{ shrink: true }}
              value={new Date(editableSnapshot.session_start_time)
                .toISOString()
                .substring(0, 10)}
              onChange={(e) =>
                handleInputChange('session_start_date', e.target.value)
              }
            />

            <TextField
              type="time"
              size="small"
              label="Time"
              InputLabelProps={{ shrink: true }}
              value={new Date(editableSnapshot.session_start_time)
                .toTimeString()
                .substring(0, 5)}
              onChange={(e) =>
                handleInputChange('session_start_time', e.target.value)
              }
            />

            <TextField
              type="number"
              size="small"
              label="Start $"
              value={editableSnapshot.session_start_value}
              onChange={(e) =>
                handleInputChange('session_start_value', e.target.value)
              }
            />

            <TextField
              type="number"
              size="small"
              label="Goal $"
              value={editableSnapshot.session_goal_value}
              onChange={(e) =>
                handleInputChange('session_goal_value', e.target.value)
              }
            />
          </Stack>

          <Stack spacing={1} direction="row" sx={{ mt: 1 }}>
            <Button size="small" variant="contained" onClick={handleSave}>
              Save
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<RestartAltIcon />}
              onClick={onReset}
            >
              Reset
            </Button>
          </Stack>

          <Button size="small" sx={{ mt: 0.5 }} onClick={flipCard}>
            Close
          </Button>
        </Card>
      </Box>
    </Box>
  );
}

PortfolioSessionCard.propTypes = {
  snapshot: PropTypes.object,
  onModify: PropTypes.func,
  onReset: PropTypes.func
};
