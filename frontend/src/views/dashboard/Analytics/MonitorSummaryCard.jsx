// MonitorSummaryCard.jsx
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import { IconShieldCheck, IconPlanet, IconSatellite, IconCurrencyDollar } from '@tabler/icons-react';

export default function MonitorSummaryCard() {
  const theme = useTheme();

  const blockSX = {
    p: 2,
    border: '1px solid',
    borderColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center'
  };

  const iconSX = {
    width: 40,
    height: 40,
    color: 'secondary.main',
    borderRadius: '14px',
    p: 1,
    bgcolor: theme.palette.mode === ThemeMode.DARK ? 'background.default' : 'primary.light',
    marginBottom: 3
  };

  return (
    <MainCard content={false}>
      <Grid container>
        <Grid sx={blockSX} item xs={6}>
          <IconShieldCheck stroke={1.5} style={iconSX} />
          <Typography variant="h5">4:34 PM</Typography>
          <Typography variant="subtitle2">SONIC</Typography>
        </Grid>
        <Grid sx={blockSX} item xs={6}>
          <IconPlanet stroke={1.5} style={iconSX} />
          <Typography variant="h5">1:15 PM</Typography>
          <Typography variant="subtitle2">JUPITER</Typography>
        </Grid>
        <Grid sx={blockSX} item xs={6}>
          <IconCurrencyDollar stroke={1.5} style={iconSX} />
          <Typography variant="h5">11:47 AM</Typography>
          <Typography variant="subtitle2">PRICE</Typography>
        </Grid>
        <Grid sx={blockSX} item xs={6}>
          <IconSatellite stroke={1.5} style={iconSX} />
          <Typography variant="h5">9:23 AM</Typography>
          <Typography variant="subtitle2">XCOM</Typography>
        </Grid>
      </Grid>
    </MainCard>
  );
}
