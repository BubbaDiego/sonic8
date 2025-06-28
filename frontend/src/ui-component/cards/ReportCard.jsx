import PropTypes from 'prop-types';
// material-ui
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// project imports
import MainCard from './MainCard';

export default function ReportCard({ primary, secondary, iconPrimary, color }) {
  const IconPrimary = iconPrimary;
  const primaryIcon = iconPrimary ? <IconPrimary fontSize="large" /> : null;

  return (
    <MainCard>
      <Grid container sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Grid>
          <Stack spacing={1}>
            <Typography variant="h3">{primary}</Typography>
            <Typography variant="body1">{secondary}</Typography>
          </Stack>
        </Grid>
        <Grid>
          <Typography variant="h2" sx={{ color }}>
            {primaryIcon}
          </Typography>
        </Grid>
      </Grid>
    </MainCard>
  );
}

ReportCard.propTypes = { primary: PropTypes.any, secondary: PropTypes.any, iconPrimary: PropTypes.any, color: PropTypes.any };
