import React from 'react';
import { Stack, Box, Button } from '@mui/material';
import MemoryIcon from '@mui/icons-material/Memory';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import SmsIcon from '@mui/icons-material/Sms';
import CampaignIcon from '@mui/icons-material/Campaign';

/**
 * Re-usable bar with the four “update” / “notification” buttons that appear
 * at the bottom of every monitor card.
 *
 * Props
 * ――――
 * • cfg    – object with boolean flags { system, voice, sms, tts }
 * • toggle – function(key) to flip a boolean in the parent cfg
 */
const ITEMS = [
  { key: 'system', label: 'System', icon: MemoryIcon,        color: 'info'    },
  { key: 'voice',  label: 'Voice',  icon: RecordVoiceOverIcon, color: 'success' },
  { key: 'sms',    label: 'SMS',    icon: SmsIcon,            color: 'warning' },
  { key: 'tts',    label: 'TTS',    icon: CampaignIcon,       color: 'error'   }
];

export default function MonitorUpdateBar({ cfg = {}, toggle, sx = {} }) {
  return (
    <Box
      /* framed wrapper */
      sx={{
        mt: 3,
        p: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        backgroundColor: 'background.paper',
        display: 'flex',
        justifyContent: 'center',
        ...sx
      }}
    >
      <Stack direction="row" spacing={3}>
        {ITEMS.map(({ key, label, icon: Icon, color }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button
              size="small"
              variant={cfg[key] ? 'contained' : 'outlined'}
              onClick={() => toggle(key)}
            >
              {label}
            </Button>
            <Icon fontSize="small" sx={{ mt: 0.5 }} color={cfg[key] ? color : 'disabled'} />
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
