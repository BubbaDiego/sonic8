import React from 'react';
import { Stack, Box, Button } from '@mui/material';
import MemoryIcon from '@mui/icons-material/Memory';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import SmsIcon from '@mui/icons-material/Sms';
import CampaignIcon from '@mui/icons-material/Campaign';

const ITEMS = [
  { key: 'system', label: 'System', icon: MemoryIcon,          color: 'info'    },
  { key: 'voice',  label: 'Voice',  icon: RecordVoiceOverIcon, color: 'success' },
  { key: 'sms',    label: 'SMS',    icon: SmsIcon,             color: 'warning' },
  { key: 'tts',    label: 'TTS',    icon: CampaignIcon,        color: 'error'   }
];

export default function MonitorUpdateBar({ cfg = {}, toggle, sx = {}, endAdornment = null }) {
  return (
    <Box
      sx={{
        px: 2, py: 1.25, mt: 1.5,
        display: 'flex',
        alignItems: 'center',
        borderTop: '1px solid',
        borderColor: 'divider',
        ...sx
      }}
    >
      <Stack direction="row" spacing={3}>
        {ITEMS.map(({ key, label, icon: Icon, color }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button
              size="small"
              variant={cfg[key] ? 'contained' : 'outlined'}
              onClick={() => toggle?.(key)}
            >
              {label}
            </Button>
            <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
          </Box>
        ))}
      </Stack>
      <Box sx={{ ml: 'auto' }}>{endAdornment}</Box>
    </Box>
  );
}

