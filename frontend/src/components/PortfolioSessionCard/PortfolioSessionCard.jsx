import React from 'react';
import PropTypes from 'prop-types';
import { Card, Typography, Avatar, IconButton, Box, LinearProgress, Stack, Paper } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

const cannedSnapshot = {
  session_start_time: new Date('2025-07-13T13:39:41'),
  current_session_value: 164.41,
  session_performance_value: 0,
  session_start_value: 100,
  session_goal_value: 200
};

export default function PortfolioSessionCard({ snapshot = cannedSnapshot, onModify, onReset }) {
  const number = (n) => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });

  const progress = snapshot.session_goal_value
    ? Math.min(100, (snapshot.current_session_value / snapshot.session_goal_value) * 100)
    : 0;

  const sessionDate = snapshot.session_start_time
    ? new Date(snapshot.session_start_time)
    : new Date();

  return (
    <Box>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 2 }}>
        <Avatar src="/static/images/bubba_icon.png" alt="Session Avatar" sx={{ width: 64, height: 64 }} />

        <Typography variant="h4" sx={{ mt: 2 }}>{number(snapshot.current_session_value)} USD</Typography>

        <Typography variant="subtitle1" color={snapshot.session_performance_value >= 0 ? 'success.main' : 'error.main'} sx={{ mt: 1 }}>
          {snapshot.session_performance_value >= 0 ? '+' : ''}
          {number(snapshot.session_performance_value)} ({number((snapshot.session_performance_value / snapshot.session_start_value) * 100)}%)
        </Typography>
        <Typography variant="subtitle2">Goal: {number(snapshot.session_goal_value)} USD</Typography>
        <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 2, width: '100%', mt: 1 }} />

        <Paper elevation={3} sx={{ padding: 1.5, borderRadius: 2, width: '80%', mt: 2 }}>
          <Stack spacing={1} alignItems="center">
            <Stack direction="row" spacing={0.5} alignItems="center">
              <CalendarTodayIcon fontSize="small" />
              <Typography variant="subtitle2">{`${sessionDate.getMonth() + 1}/${sessionDate.getDate()}`}</Typography>
            </Stack>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <AccessTimeIcon fontSize="small" />
              <Typography variant="subtitle2">{sessionDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</Typography>
            </Stack>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <AttachMoneyIcon fontSize="small" />
              <Typography variant="subtitle2">{number(snapshot.session_start_value)} USD</Typography>
            </Stack>
          </Stack>
        </Paper>

        <Box sx={{ mt: 2 }}>
          <IconButton color="primary" onClick={onModify}><EditIcon /></IconButton>
          <IconButton color="secondary" onClick={onReset}><RestartAltIcon /></IconButton>
        </Box>
      </Card>
    </Box>
  );
}

PortfolioSessionCard.propTypes = {
  snapshot: PropTypes.object,
  onModify: PropTypes.func,
  onReset: PropTypes.func,
};
