import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';
import { useNavigate } from 'react-router-dom';
import DirectionsRunIcon from '@mui/icons-material/DirectionsRun';

import { ThemeMode } from 'config';

// ==============================|| CYCLONE RUN SECTION ||============================== //

export default function CycloneRunSection() {
  const theme = useTheme();
  const navigate = useNavigate();

  const handleClick = () => {
    navigate('/cyclone/run');
  };

  return (
    <Box sx={{ ml: 2 }}>
      <Tooltip title="Cyclone Run">
        <Avatar
          variant="rounded"
          sx={{
            ...theme.typography.commonAvatar,
            ...theme.typography.mediumAvatar,
            bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
            color: 'primary.dark',
            '&:hover': {
              bgcolor: 'primary.main',
              color: 'primary.light'
            }
          }}
          onClick={handleClick}
        >
          <DirectionsRunIcon fontSize="small" />
        </Avatar>
      </Tooltip>
    </Box>
  );
}
