import React from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  CardActions,
  Typography,
  LinearProgress,
  IconButton,
  Tooltip,
  Stack
} from '@mui/material';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import EditNoteIcon from '@mui/icons-material/EditNote';

const number = n => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });

/**
 * PortfolioSessionCard – shows real‑time session KPIs and lets the
 * user tweak / restart the session.
 *
 * Layout: header (title + value), body (metrics grid + progress bar),
 * footer (action buttons).  Width is governed by the grid slot; height
 * stretches to available space so the text remains readable.
 */
export default function PortfolioSessionCard({
  snapshot,
  onModify    = () => {},
  onReset     = () => {},
  onEnd       = null     // optional “close session” action
}) {
  if (!snapshot?.session_start_time) {
    return (
      <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No active session
        </Typography>
      </Card>
    );
  }

  const {
    current_session_value,
    session_start_value,
    session_goal_value,
    session_performance_value
  } = snapshot;

  const delta = session_performance_value;
  const pct   = session_goal_value
    ? Math.min(100, (current_session_value / session_goal_value) * 100)
    : 0;

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader
        title="Current Session"
        subheader={`Started ${new Date(snapshot.session_start_time).toLocaleString()}`}
        sx={{ pb: 0 }}
      />

      <CardContent sx={{ flexGrow: 1 }}>
        <Stack spacing={1}>
          <Typography variant="h6">
            {number(current_session_value)}&nbsp;USD
          </Typography>

          <Typography variant="subtitle2" color={delta >= 0 ? 'success.main' : 'error.main'}>
            {delta >= 0 ? '+' : ''}
            {number(delta)} ({number((delta / session_start_value) * 100)}%)
          </Typography>

          <LinearProgress
            variant="determinate"
            value={pct}
            sx={{ height: 10, borderRadius: 1 }}
          />
          <Typography variant="caption" align="right">
            Goal {number(session_goal_value)}
          </Typography>

          {/* Mini metric grid */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 0.5,
              mt: 1
            }}
          >
            <Metric label="Tot. Value"    value={snapshot.total_value} />
            <Metric label="Collateral"     value={snapshot.total_collateral} />
            <Metric label="Avg Lev."       value={snapshot.avg_leverage} />
            <Metric label="Heat Index"     value={snapshot.avg_heat_index} />
          </Box>
        </Stack>
      </CardContent>

      <CardActions sx={{ justifyContent: 'flex-end', pt: 0 }}>
        <Tooltip title="Modify session settings">
          <IconButton size="small" onClick={onModify}>
            <EditNoteIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        <Tooltip title="Reset session">
          <IconButton size="small" onClick={onReset}>
            <RestartAltIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        {onEnd && (
          <Tooltip title="End session">
            <IconButton size="small" onClick={onEnd}>
              {/* use a stop icon of your choice */}
            </IconButton>
          </Tooltip>
        )}
      </CardActions>
    </Card>
  );
}

function Metric({ label, value }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2">
        {number(value)}
      </Typography>
    </Box>
  );
}

Metric.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number
};

PortfolioSessionCard.propTypes = {
  snapshot:  PropTypes.object,
  onModify:  PropTypes.func,
  onReset:   PropTypes.func,
  onEnd:     PropTypes.func
};
