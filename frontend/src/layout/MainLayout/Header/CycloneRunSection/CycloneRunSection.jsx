// material-ui
import { useState } from 'react';
import { useTheme } from '@mui/material/styles';
import { keyframes } from '@mui/system';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';

// project imports
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import { runFullCycle, runPositionUpdate, runPriceUpdate, deleteAllData } from 'api/cyclone';
import { refreshPositions } from 'api/positions';
import { refreshLatestPortfolio, refreshPortfolioHistory } from 'api/portfolio';
import { runSonicCycle } from 'api/sonicMonitor';
import { refreshMonitorStatus } from 'api/monitorStatus';
import { useDispatch } from 'store';
import { openSnackbar } from 'store/slices/snackbar';

// assets
import { IconRefresh, IconEdit, IconTrash, IconTornado } from '@tabler/icons-react';
const SonicBurstIcon = '/static/images/super_sonic.png';

export const spin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(-360deg); }
`;

// ==============================|| HEADER CONTENT - CYCLONE RUN ||============================== //

export default function CycloneRunSection() {
  const theme = useTheme();
  const dispatch = useDispatch();
  const { cycloneRefreshDelay = 6000 } = useConfig();
  const [sonicRunning, setSonicRunning] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const menuOpen = Boolean(menuAnchorEl);

  /* ----------  update-menu helpers ---------- */
  const handleMenuOpen = (event) => setMenuAnchorEl(event.currentTarget);
  const handleMenuClose = () => setMenuAnchorEl(null);
  const withMenuClose = (fn) => () => {
    handleMenuClose();
    fn();
  };

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

  const handleSonicCycle = () => {
    setSonicRunning(true);
    runSonicCycle()
      .then(() => {
        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
          refreshMonitorStatus();
          setSonicRunning(false);
        }, cycloneRefreshDelay);

        dispatch(
          openSnackbar({
            open: true,
            message: 'Sonic Cycle Success',
            variant: 'alert',
            alert: { color: 'success' },
            close: false
          })
        );
      })
      .catch((error) => {
        console.error(error);
        setSonicRunning(false);
        dispatch(
          openSnackbar({
            open: true,
            message: 'Sonic Cycle Error',
            variant: 'alert',
            alert: { color: 'error' },
            close: false,
            severity: 'error'
          })
        );
      });
  };

  const handlePriceUpdate = () => {
    runPriceUpdate()
      .then(() => {

        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
        }, cycloneRefreshDelay);

        dispatch(
          openSnackbar({
            open: true,
            message: 'Price Update Success',
            variant: 'alert',
            alert: { color: 'success' },
            close: false
          })
        );
      })
      .catch((error) => {
        console.error(error);
        dispatch(
          openSnackbar({
            open: true,
            message: 'Price Update Error',
            variant: 'alert',
            alert: { color: 'error' },
            close: false,
            severity: 'error'
          })
        );
      });
  };

  const handlePositionUpdate = () => {
    runPositionUpdate()
      .then(() => {

        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
        }, cycloneRefreshDelay);

        dispatch(
          openSnackbar({
            open: true,
            message: 'Position Update Success',
            variant: 'alert',
            alert: { color: 'success' },
            close: false
          })
        );
      })
      .catch((error) => {
        console.error(error);
        dispatch(
          openSnackbar({
            open: true,
            message: 'Position Update Error',
            variant: 'alert',
            alert: { color: 'error' },
            close: false,
            severity: 'error'
          })
        );
      });
  };

  const handleDeleteAllData = () => {
    deleteAllData()
      .then(() => {

        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
        }, 1000);

        dispatch(
          openSnackbar({
            open: true,
            message: 'Data Delete Success',
            variant: 'alert',
            alert: { color: 'success' },
            close: false
          })
        );
      })
      .catch((error) => {
        console.error(error);
        dispatch(
          openSnackbar({
            open: true,
            message: 'Data Delete Error',
            variant: 'alert',
            alert: { color: 'error' },
            close: false,
            severity: 'error'
          })
        );
      });
  };

  const handleFullCycle = () => {
    runFullCycle()
      .then(() => {

        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
        }, cycloneRefreshDelay);

        dispatch(
          openSnackbar({
            open: true,
            message: 'Full Cycle Success',
            variant: 'alert',
            alert: { color: 'success' },
            close: false
          })
        );
      })
      .catch((error) => {
        console.error(error);
        dispatch(
          openSnackbar({
            open: true,
            message: 'Full Cycle Error',
            variant: 'alert',
            alert: { color: 'error' },
            close: false,
            severity: 'error'
          })
        );
      });
  };

  return (
    <Box sx={{ ml: 2 }}>
      <Stack direction="row" spacing={1}>

        <Tooltip title="Sonic Cycle">
          <Avatar
            variant="circular"
            sx={{
              ...avatarSX,
              animation: sonicRunning ? `${spin} 2s linear infinite` : 'none'
            }}
            onClick={handleSonicCycle}
          >
            <Box
              component="img"
              src={SonicBurstIcon}
              alt="sonic"
              sx={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
            />
          </Avatar>
        </Tooltip>
        {/* single “Update“ avatar that shows the dropdown */}
        <Tooltip title="Update">
          <Avatar variant="rounded" sx={avatarSX} onClick={handleMenuOpen}>
            <IconRefresh size="20px" />
          </Avatar>
        </Tooltip>

        <Menu
          anchorEl={menuAnchorEl}
          open={menuOpen}
          onClose={handleMenuClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <MenuItem onClick={withMenuClose(handleDeleteAllData)}>
            <ListItemIcon><IconTrash size="18px" /></ListItemIcon>
            <ListItemText primary="Delete\u202fAll" />
          </MenuItem>
          <MenuItem onClick={withMenuClose(handlePositionUpdate)}>
            <ListItemIcon><IconEdit size="18px" /></ListItemIcon>
            <ListItemText primary="Update\u202fPositions" />
          </MenuItem>
          <MenuItem onClick={withMenuClose(handlePriceUpdate)}>
            <ListItemIcon><IconRefresh size="18px" /></ListItemIcon>
            <ListItemText primary="Update\u202fPrices" />
          </MenuItem>
          <MenuItem onClick={withMenuClose(handleFullCycle)}>
            <ListItemIcon><IconTornado size="18px" /></ListItemIcon>
            <ListItemText primary="Cyclone\u202fCycle" />
          </MenuItem>
        </Menu>
      </Stack>
    </Box>
  );
}
