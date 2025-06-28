import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import ButtonBase from '@mui/material/ButtonBase';
import Grid from '@mui/material/Grid';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';

// project imports
import ColorOptions from '../ColorOptions';
import { ThemeMode } from 'config';
import Avatar from 'ui-component/extended/Avatar';

// assets
import CheckIcon from '@mui/icons-material/Check';

function Color({ bg, id, colors, label, handelFilter }) {
  const theme = useTheme();

  return (
    <Grid>
      <Tooltip title={label}>
        <ButtonBase sx={{ borderRadius: '50%' }} onClick={() => handelFilter('colors', id)}>
          <Avatar
            color="inherit"
            size="badge"
            sx={{
              bgcolor: bg,
              color: theme.palette.mode === ThemeMode.DARK ? 'grey.800' : 'grey.50',
              opacity: colors.some((item) => item === id) ? 0.6 : 1
            }}
          >
            {colors.some((item) => item === id) ? (
              <CheckIcon sx={{ color: theme.palette.mode === ThemeMode.DARK ? 'dark.800' : 'grey.50' }} fontSize="inherit" />
            ) : (
              <></>
            )}
          </Avatar>
        </ButtonBase>
      </Tooltip>
    </Grid>
  );
}

// ==============================|| PRODUCT - COLOR ||============================== //

export default function Colors({ colors, handelFilter }) {
  const [isColorsLoading, setColorLoading] = useState(true);
  useEffect(() => {
    setColorLoading(false);
  }, []);

  return (
    <>
      {isColorsLoading ? (
        <Grid size={12}>
          <Skeleton variant="rectangular" width="100%" height={158} />
        </Grid>
      ) : (
        <Grid container spacing={1} sx={{ alignItems: 'center' }}>
          {ColorOptions.map((color, index) => (
            <Color key={index} id={color.value} bg={color.bg} label={color.label} colors={colors} handelFilter={handelFilter} />
          ))}
        </Grid>
      )}
    </>
  );
}

Color.propTypes = {
  bg: PropTypes.string,
  id: PropTypes.string,
  colors: PropTypes.array,
  label: PropTypes.string,
  handelFilter: PropTypes.func
};

Colors.propTypes = { colors: PropTypes.array, handelFilter: PropTypes.func };
