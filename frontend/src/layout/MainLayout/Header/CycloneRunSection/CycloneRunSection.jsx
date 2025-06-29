// material-ui
import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';

// project imports
import { ThemeMode } from 'config';

// assets
import { IconRefresh, IconEdit, IconTrash, IconTornado } from '@tabler/icons-react';

// ==============================|| HEADER CONTENT - CYCLONE RUN ||============================== //

export default function CycloneRunSection() {
  const theme = useTheme();

  const avatarSX = {
    ...theme.typography.commonAvatar,
    ...theme.typography.mediumAvatar,
    border: '1px solid',
    borderColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
    bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
    color: 'primary.dark',
    transition: 'all .2s ease-in-out',
    '&:hover': {
      borderColor: 'primary.main',
      bgcolor: 'primary.main',
      color: 'primary.light'
    }
  };

  return (
    <Box sx={{ ml: 2 }}>
      <Stack direction="row" spacing={1}>
        <Tooltip title="Price Update">
          <Avatar variant="rounded" sx={avatarSX}>
            <IconRefresh size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Position Update">
          <Avatar variant="rounded" sx={avatarSX}>
            <IconEdit size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Delete">
          <Avatar variant="rounded" sx={avatarSX}>
            <IconTrash size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Full Cyclone">
          <Avatar variant="rounded" sx={avatarSX}>
            <IconTornado size="20px" />
          </Avatar>
        </Tooltip>
      </Stack>
    </Box>
  );
}
