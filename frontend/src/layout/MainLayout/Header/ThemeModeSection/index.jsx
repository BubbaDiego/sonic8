import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';

import { IconSun, IconMoon } from '@tabler/icons-react';

import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';

export default function ThemeModeSection() {
  const theme = useTheme();
  const { mode, onChangeMode } = useConfig();

  const handleToggle = () => {
    let newMode;
    if (mode === ThemeMode.LIGHT) {
      newMode = ThemeMode.DARK;
    } else if (mode === ThemeMode.DARK) {
      newMode = ThemeMode.FUNKY;
    } else {
      newMode = ThemeMode.LIGHT;
    }
    onChangeMode(newMode);
  };

  const nextMode =
    mode === ThemeMode.LIGHT
      ? ThemeMode.DARK
      : mode === ThemeMode.DARK
        ? ThemeMode.FUNKY
        : ThemeMode.LIGHT;
  const tooltipTitle =
    nextMode === ThemeMode.DARK
      ? 'Dark Mode'
      : nextMode === ThemeMode.FUNKY
        ? 'Funky Mode'
        : 'Light Mode';

  return (
    <Box sx={{ ml: 2 }}>
      <Tooltip title={tooltipTitle}>
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
          {nextMode === ThemeMode.DARK ? (
            <IconMoon />
          ) : nextMode === ThemeMode.FUNKY ? (
            'F'
          ) : (
            <IconSun />
          )}
        </Avatar>
      </Tooltip>
    </Box>
  );
}
