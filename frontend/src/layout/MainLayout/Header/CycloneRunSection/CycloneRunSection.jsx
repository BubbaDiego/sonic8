// material-ui
import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';

// project imports
import { ThemeMode } from 'config';
import { runFullCycle, runPositionUpdate, runPriceUpdate, deleteAllData } from 'api/cyclone';
import { refreshPositions } from 'api/positions';
import { refreshLatestPortfolio, refreshPortfolioHistory } from 'api/portfolio';
import { useDispatch } from 'store';
import { openSnackbar } from 'store/slices/snackbar';

// assets
import { IconRefresh, IconEdit, IconTrash, IconTornado } from '@tabler/icons-react';

// ==============================|| HEADER CONTENT - CYCLONE RUN ||============================== //

export default function CycloneRunSection() {
  const theme = useTheme();
  const dispatch = useDispatch();
  const REFRESH_DELAY_MS = 5000;

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

  const handlePriceUpdate = () => {
    runPriceUpdate()
      .then(() => {

        setTimeout(() => {
          refreshLatestPortfolio();
          refreshPortfolioHistory();
          refreshPositions();
        }, REFRESH_DELAY_MS);

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
        }, REFRESH_DELAY_MS);

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
        }, REFRESH_DELAY_MS);

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
