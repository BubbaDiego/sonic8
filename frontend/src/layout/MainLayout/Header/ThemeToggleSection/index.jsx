import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';

import { IconSun, IconMoon } from '@tabler/icons-react';

import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';

export default function ThemeToggleSection() {
  const theme = useTheme();
  const { mode, onChangeMode } = useConfig();

  const handleToggle = () => {
    onChangeMode(mode === ThemeMode.DARK ? ThemeMode.LIGHT : ThemeMode.DARK);
  };

  return (
    <Box sx={{ ml: 2 }}>
      <Tooltip title={mode === ThemeMode.DARK ? 'Light Mode' : 'Dark Mode'}>
        <Avatar
          variant="rounded"
          sx={{
            ...theme.typography.commonAvatar,
            ...theme.typography.mediumAvatar,
            border: '1px solid',
            borderColor: mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
            bgcolor: mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
            color: 'primary.dark',
            transition: 'all .2s ease-in-out',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'primary.main',
              color: 'primary.light'
            }
          }}
          onClick={handleToggle}
          color="inherit"
        >
          {mode === ThemeMode.DARK ? <IconSun size="20px" /> : <IconMoon size="20px" />}
        </Avatar>
      </Tooltip>
    </Box>
  );
}
