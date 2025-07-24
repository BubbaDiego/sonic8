// material-ui
import { useTheme } from '@mui/material/styles';
import { keyframes } from '@mui/system';
import { useState } from 'react';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import { motion } from 'framer-motion';

// project imports
import { ThemeMode } from 'config';
import useConfig from 'hooks/useConfig';
import { runFullCycle, runPositionUpdate, runPriceUpdate, deleteAllData } from 'api/cyclone';
import { refreshPositions } from 'api/positions';
import { refreshLatestPortfolio, refreshPortfolioHistory } from 'api/portfolio';
import { runSonicMonitor } from 'api/sonicMonitor';
import { refreshMonitorStatus } from 'api/monitorStatus';
import { useDispatch } from 'store';
import { openSnackbar } from 'store/slices/snackbar';

// assets
import { IconRefresh, IconEdit, IconTrash, IconTornado } from '@tabler/icons-react';
const SonicBurstIcon = '/static/images/sonic_burst.png';

// ==============================|| HEADER CONTENT - CYCLONE RUN ||============================== //

export default function CycloneRunSection() {
  const theme = useTheme();
  const dispatch = useDispatch();
  const { cycloneRefreshDelay = 6000 } = useConfig();
  const [sonicRunning, setSonicRunning] = useState(false);

  const [running, setRunning] = useState(false);

  const spin = keyframes`
    from { transform: rotate(0deg); }
    to { transform: rotate(-360deg); }
  `;

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

  const handleSonicCycle = () => {
    setRunning(true);
    runSonicMonitor()
      .then(() => {
        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
          refreshMonitorStatus();
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
      })
      .finally(() => setRunning(false));
  };

  return (
    <Box sx={{ ml: 2 }}>
      <Stack direction="row" spacing={1}>

        <Tooltip title="Sonic Cycle">
          {sonicRunning ? (
            <motion.div animate={{ rotate: -360 }} transition={{ repeat: Infinity, repeatType: 'loop', duration: 2, ease: 'linear' }}>
              <Avatar variant="circular" sx={avatarSX}>
                <Box component="img" src={SonicBurstIcon} alt="sonic" sx={{ width: '20px' }} />
              </Avatar>
            </motion.div>
          ) : (
            <Avatar variant="circular" sx={avatarSX} onClick={handleSonicCycle}>
              <Box component="img" src={SonicBurstIcon} alt="sonic" sx={{ width: '20px' }} />
            </Avatar>
          )

        </Tooltip>
        <Tooltip title="Price Update">
          <Avatar variant="rounded" sx={avatarSX} onClick={handlePriceUpdate}>
            <IconRefresh size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Position Update">
          <Avatar variant="rounded" sx={avatarSX} onClick={handlePositionUpdate}>
            <IconEdit size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Delete">
          <Avatar variant="rounded" sx={avatarSX} onClick={handleDeleteAllData}>
            <IconTrash size="20px" />
          </Avatar>
        </Tooltip>
        <Tooltip title="Full Cyclone">
          <Avatar variant="rounded" sx={avatarSX} onClick={handleFullCycle}>
            <IconTornado size="20px" />
          </Avatar>
        </Tooltip>
      </Stack>
    </Box>
  );
}
