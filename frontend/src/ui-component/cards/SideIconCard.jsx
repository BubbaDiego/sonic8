import PropTypes from 'prop-types';
// material-ui
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// =============================|| SIDE ICON CARD ||============================= //

export default function SideIconCard({ iconPrimary, primary, secondary, secondarySub, color, bgcolor }) {
  const IconPrimary = iconPrimary;
  const primaryIcon = iconPrimary !== undefined ? <IconPrimary /> : null;

  return (
    <Card sx={{ bgcolor: bgcolor || '', position: 'relative' }}>
      <Grid container columnSpacing={2} sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Grid sx={{ bgcolor: color, py: 3.5, px: 0 }} size={4}>
          <Typography variant="h5" sx={{ textAlign: 'center', color: '#fff', '& > svg': { width: 32, height: 32 } }} align="center">
            {primaryIcon}
          </Typography>
        </Grid>
        <Grid size={8}>
          <Stack spacing={1} sx={{ alignItems: { xs: 'center', sm: 'flex-start' }, justifyContent: 'space-between' }}>
            <Typography variant="h3" {...(bgcolor && { sx: { color: '#fff' } })}>
              {primary}
            </Typography>
            <Typography variant="body2" sx={{ color: bgcolor ? '#fff' : 'grey.600', display: 'flex', gap: 0.25 }}>
              {secondary}{' '}
              <Box component="span" sx={{ color }}>
                {secondarySub}
              </Box>
            </Typography>
          </Stack>
        </Grid>
      </Grid>
    </Card>
  );
}

SideIconCard.propTypes = {
  iconPrimary: PropTypes.object,
  primary: PropTypes.any,
  secondary: PropTypes.any,
  secondarySub: PropTypes.string,
  color: PropTypes.any,
  bgcolor: PropTypes.string
};
