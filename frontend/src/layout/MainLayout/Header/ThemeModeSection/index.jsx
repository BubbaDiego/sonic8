import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';

import { IconSun, IconMoon, IconDeviceDesktop } from '@tabler/icons-react';

import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';

export default function ThemeModeSection() {
  const theme = useTheme();
  const { mode, onChangeMode } = useConfig();

  const themeOrder = [ThemeMode.LIGHT, ThemeMode.DARK, ThemeMode.SYSTEM];
  const nextMode = themeOrder[(themeOrder.indexOf(mode) + 1) % themeOrder.length];

  const iconMap = {
    [ThemeMode.LIGHT]: <IconMoon />,
    [ThemeMode.DARK]: <IconDeviceDesktop />,
    [ThemeMode.SYSTEM]: <IconSun />
  };

  const tooltipMap = {
    [ThemeMode.LIGHT]: 'Dark Mode',
    [ThemeMode.DARK]: 'System Mode',
    [ThemeMode.SYSTEM]: 'Light Mode'
  };


  const handleToggle = () => {
    onChangeMode(nextMode);

  const iconMap = {
    [ThemeMode.LIGHT]: <IconMoon />,
    [ThemeMode.DARK]: <IconDeviceDesktop />,
    [ThemeMode.SYSTEM]: <IconSun />

  };

  return (
    <Box sx={{ ml: 2 }}>
      <Tooltip title={tooltipMap[mode]}>
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
          {iconMap[mode]}
        </Avatar>
      </Tooltip>
    </Box>
  );
}
