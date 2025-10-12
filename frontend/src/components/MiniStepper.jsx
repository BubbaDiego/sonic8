import React from 'react';
import { Stack, IconButton, Chip, Tooltip } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';

export default function MiniStepper({
  value = 0,
  onChange,
  step = 1,
  min = 0,
  max = 100,
  label = 'Blast radius'
}) {
  const round = (v) => Math.round(v * 100) / 100;
  const inc = () => onChange?.(Math.min(max, round(Number(value || 0) + step)));
  const dec = () => onChange?.(Math.max(min, round(Number(value || 0) - step)));

  return (
    <Stack direction="row" spacing={0.5} alignItems="center"
      sx={{ opacity: 0.85, transition: 'opacity .15s ease-in-out', '&:hover': { opacity: 1 } }}>
      <Tooltip title={`Decrease ${label}`}>
        <span>
          <IconButton size="small" onClick={dec} disabled={(value ?? 0) <= min}>
            <RemoveIcon fontSize="inherit" />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title={`${label}: ${value}`}>
        <Chip
          label={String(value ?? 0)}
          size="small"
          sx={{ fontWeight: 600, minWidth: 36, height: 26, '& .MuiChip-label': { px: 1 } }}
        />
      </Tooltip>
      <Tooltip title={`Increase ${label}`}>
        <span>
          <IconButton size="small" onClick={inc} disabled={(value ?? 0) >= max}>
            <AddIcon fontSize="inherit" />
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );
}

