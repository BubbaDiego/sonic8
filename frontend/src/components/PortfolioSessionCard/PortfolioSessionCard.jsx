import React from 'react';
import PropTypes from 'prop-types';
import { Card, Typography, Avatar, IconButton, Box, LinearProgress, Stack } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import RestartAltIcon from '@mui/icons-material/RestartAlt';

export default function PortfolioSessionCard({ snapshot, onReset }) {
  if (!snapshot?.session_start_time) {
    return (
      <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No active session
        </Typography>
      </Card>
    );
  }

  const number = (n) => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });

  const progress = snapshot.session_goal_value
    ? Math.min(100, (snapshot.current_session_value / snapshot.session_goal_value) * 100)
    : 0;

  return (
    <Box>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 2 }}>
        <Avatar src="/static/images/bubba_icon.png" alt="Session Avatar" sx={{ width: 64, height: 64 }} />
        <Typography variant="h5">Current Session</Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Started: {new Date(snapshot.session_start_time).toLocaleString()}
        </Typography>

        <Stack spacing={1} sx={{ width: '100%', mt: 2 }}>
          <Typography variant="h4">{number(snapshot.current_session_value)} USD</Typography>
          <Typography variant="subtitle1" color={snapshot.session_performance_value >= 0 ? 'success.main' : 'error.main'}>
            {snapshot.session_performance_value >= 0 ? '+' : ''}
            {number(snapshot.session_performance_value)} ({number((snapshot.session_performance_value / snapshot.session_start_value) * 100)}%)
          </Typography>
          <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 2 }} />

          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1, mt: 1 }}>
            <Metric label="Tot. Value" value={snapshot.total_value} />
            <Metric label="Collateral" value={snapshot.total_collateral} />
            <Metric label="Avg Leverage" value={snapshot.avg_leverage} />
            <Metric label="Heat Index" value={snapshot.avg_heat_index} />
          </Box>
        </Stack>

        <Box>
          <IconButton color="primary" onClick={() => {}}><EditIcon /></IconButton>
          <IconButton color="secondary" onClick={onReset}><RestartAltIcon /></IconButton>
        </Box>
      </Card>
    </Box>
  );
}

function Metric({ label, value }) {
  const number = (n) => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="body2">{number(value)}</Typography>
    </Box>
  );
}

PortfolioSessionCard.propTypes = {
  snapshot: PropTypes.object,
  onReset: PropTypes.func,
};
