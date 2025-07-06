// StatsSummaryCard.jsx
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import MainCard from 'ui-component/cards/MainCard';
import { ThemeMode } from 'config';
import { IconShare, IconAccessPoint, IconCircles, IconCreditCard } from '@tabler/icons-react';

export default function StatsSummaryCard() {
  const theme = useTheme();

  const blockSX = {
    p: 2.5,
    borderLeft: '1px solid ',
    borderBottom: '1px solid ',
    borderLeftColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200',
    borderBottomColor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'grey.200'
  };

  return (
    <MainCard
      content={false}
      sx={{
        '& svg': {
          width: 50,
          height: 50,
          color: 'secondary.main',
          borderRadius: '14px',
          p: 1.25,
          bgcolor: theme.palette.mode === ThemeMode.DARK ? 'background.default' : 'primary.light'
        }
      }}
    >
      <Grid container spacing={0} sx={{ alignItems: 'center' }}>
        <Grid sx={blockSX} size={{ xs: 12, sm: 6 }}>
          <Grid container spacing={1} sx={{ alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' } }}>
            <Grid>
              <IconShare stroke={1.5} />
            </Grid>
            <Grid size={{ sm: 'grow' }}>
              <Typography variant="h5" align="center">1000</Typography>
              <Typography variant="subtitle2" align="center">SHARES</Typography>
            </Grid>
          </Grid>
        </Grid>
        <Grid sx={blockSX} size={{ xs: 12, sm: 6 }}>
          <Grid container spacing={1} sx={{ alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' } }}>
            <Grid>
              <IconAccessPoint stroke={1.5} />
            </Grid>
            <Grid size={{ sm: 'grow' }}>
              <Typography variant="h5" align="center">600</Typography>
              <Typography variant="subtitle2" align="center">NETWORK</Typography>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      <Grid container spacing={0} sx={{ alignItems: 'center' }}>
        <Grid sx={blockSX} size={{ xs: 12, sm: 6 }}>
          <Grid container spacing={1} sx={{ alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' } }}>
            <Grid>
              <IconCircles stroke={1.5} />
            </Grid>
            <Grid size={{ sm: 'grow' }}>
              <Typography variant="h5" align="center">3550</Typography>
              <Typography variant="subtitle2" align="center">RETURNS</Typography>
            </Grid>
          </Grid>
        </Grid>
        <Grid sx={blockSX} size={{ xs: 12, sm: 6 }}>
          <Grid container spacing={1} sx={{ alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' } }}>
            <Grid>
              <IconCreditCard stroke={1.5} />
            </Grid>
            <Grid size={{ sm: 'grow' }}>
              <Typography variant="h5" align="center">100%</Typography>
              <Typography variant="subtitle2" align="center">ORDER</Typography>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </MainCard>
  );
}
