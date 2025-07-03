import PropTypes from 'prop-types';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// project imports
import MainCard from './MainCard';

// ============================|| HOVER DATA CARD ||============================ //

export default function HoverDataCard({ title, iconPrimary, primary, secondary, color }) {
  const IconPrimary = iconPrimary;
  const primaryIcon = iconPrimary !== undefined ? <IconPrimary fontSize="large" sx={{ width: 20, height: 20, color }} /> : null;

  return (
    <MainCard>
      <Stack spacing={1.75} sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" color="inherit">
          {title}
        </Typography>
        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', mx: 'auto' }}>
          {primaryIcon}
          <Typography variant="h3">{primary}</Typography>
        </Stack>
        <Typography variant="body2" color="textSecondary">
          {secondary}
        </Typography>
      </Stack>
    </MainCard>
  );
}

HoverDataCard.propTypes = {
  title: PropTypes.any,
  iconPrimary: PropTypes.object,
  primary: PropTypes.any,
  secondary: PropTypes.any,
  color: PropTypes.any
};
