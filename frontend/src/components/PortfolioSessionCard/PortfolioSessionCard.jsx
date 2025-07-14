import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Card, Typography, Avatar, IconButton, Box, LinearProgress, Stack, Paper, Button, TextField } from '@mui/material';
import { useGetActiveSession } from 'api/session';
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

export default function PortfolioSessionCard({ snapshot: snapshotProp, onModify, onReset }) {
  const { session } = useGetActiveSession();
  const snapshot = snapshotProp || session || cannedSnapshot;
  const [flipped, setFlipped] = useState(false);
  const [editableSnapshot, setEditableSnapshot] = useState({ ...snapshot });

  useEffect(() => {
    setEditableSnapshot({ ...snapshot });
  }, [snapshot]);

  const flipCard = () => setFlipped(!flipped);

  const number = (n) => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });

  const progress = snapshot.session_goal_value
    ? Math.min(100, (snapshot.current_session_value / snapshot.session_goal_value) * 100)
    : 0;

  const handleInputChange = (field, value) => {
    setEditableSnapshot((prev) => {
      const updatedSnapshot = { ...prev };
      if (field === 'session_start_date') {
        const [year, month, day] = value.split('-');
        const currentTime = new Date(updatedSnapshot.session_start_time);
        currentTime.setFullYear(year, month - 1, day);
        updatedSnapshot.session_start_time = currentTime;
      } else if (field === 'session_start_time') {
        const [hour, minute] = value.split(':');
        const currentDate = new Date(updatedSnapshot.session_start_time);
        currentDate.setHours(hour, minute);
        updatedSnapshot.session_start_time = currentDate;
      } else {
        updatedSnapshot[field] = parseFloat(value);
      }
      return updatedSnapshot;
    });
  };

  const handleSave = () => {
    onModify(editableSnapshot);
    flipCard();
  };

  const sessionDate = snapshot.session_start_time
    ? new Date(snapshot.session_start_time)
    : new Date();

  return (
    <Box sx={{ perspective: '1000px', height: '450px', width: '100%' }}>
      <Box
        sx={{
          width: '100%',
          height: '100%',
          position: 'relative',
          transition: 'transform 0.8s',
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
        }}
      >
        {/* Front side */}
        <Card sx={{ position: 'absolute', width: '100%', height: '100%', backfaceVisibility: 'hidden', padding: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <Stack spacing={2} alignItems="center">
            <Avatar src="/static/images/bubba_icon.png" alt="Session Avatar" sx={{ width: 64, height: 64 }} />

            <Typography variant="h4">{number(snapshot.current_session_value)} USD</Typography>

            <Typography variant="subtitle1" color={snapshot.session_performance_value >= 0 ? 'success.main' : 'error.main'}>
              {snapshot.session_performance_value >= 0 ? '+' : ''}
              {number(snapshot.session_performance_value)} ({number((snapshot.session_performance_value / snapshot.session_start_value) * 100)}%)
            </Typography>
            <Typography variant="subtitle2">Goal: {number(snapshot.session_goal_value)} USD</Typography>
            <LinearProgress variant="determinate" value={progress} sx={{ width: '100%', borderRadius: 2, height: 8 }} />

            <Paper elevation={3} sx={{ padding: 1, borderRadius: 2, width: '100%', mt: 1 }}>
              <Stack direction="row" justifyContent="space-around" alignItems="center">
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <CalendarTodayIcon fontSize="small" />
                  <Typography variant="caption">{`${sessionDate.getMonth() + 1}/${sessionDate.getDate()}`}</Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <AccessTimeIcon fontSize="small" />
                  <Typography variant="caption">{sessionDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <AttachMoneyIcon fontSize="small" />
                  <Typography variant="caption">{number(snapshot.session_start_value)} USD</Typography>
                </Stack>
              </Stack>
            </Paper>

            <IconButton color="primary" onClick={flipCard}><EditIcon /></IconButton>
          </Stack>
        </Card>

        {/* Back side */}
        <Card sx={{ position: 'absolute', width: '100%', height: '100%', backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', padding: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h6">Edit Session</Typography>
          <Stack spacing={2} sx={{ mt: 2, width: '80%' }}>
            <TextField type="date" label="Start Date" InputLabelProps={{ shrink: true }} fullWidth value={new Date(editableSnapshot.session_start_time).toISOString().substring(0, 10)} onChange={(e) => handleInputChange('session_start_date', e.target.value)} />
            <TextField type="time" label="Start Time" InputLabelProps={{ shrink: true }} fullWidth value={new Date(editableSnapshot.session_start_time).toTimeString().substring(0, 5)} onChange={(e) => handleInputChange('session_start_time', e.target.value)} />
            <TextField type="number" label="Start Amount" fullWidth value={editableSnapshot.session_start_value} onChange={(e) => handleInputChange('session_start_value', e.target.value)} />
            <TextField type="number" label="Goal Amount" fullWidth value={editableSnapshot.session_goal_value} onChange={(e) => handleInputChange('session_goal_value', e.target.value)} />
          </Stack>
          <Stack spacing={2} direction="row" sx={{ mt: 2 }}>
            <Button variant="contained" onClick={handleSave}>Save</Button>
            <Button variant="outlined" startIcon={<RestartAltIcon />} onClick={onReset}>Reset</Button>
          </Stack>
          <Button sx={{ mt: 1 }} onClick={flipCard}>Close</Button>
        </Card>
      </Box>
    </Box>
  );
}

PortfolioSessionCard.propTypes = {
  snapshot: PropTypes.object,
  onModify: PropTypes.func,
  onReset: PropTypes.func,
};
