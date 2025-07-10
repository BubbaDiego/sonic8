import PropTypes from 'prop-types';
import { styled } from '@mui/material/styles';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import MainCard from 'ui-component/cards/MainCard';

const DarkWrapper = styled(MainCard)(({ theme }) => ({
  backgroundColor: theme.palette.primary.dark,
  color: theme.palette.primary.light,
  overflow: 'hidden',
  position: 'relative'
}));

const LightWrapper = styled(MainCard)(({ theme }) => ({
  backgroundColor: theme.palette.primary.light,
  color: theme.palette.primary.dark,
  overflow: 'hidden',
  position: 'relative'
}));

export default function StatCard({ label, value, secondary, variant = 'light' }) {
  const Wrapper = variant === 'dark' ? DarkWrapper : LightWrapper;

  return (
    <Wrapper>
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="h4">{value}</Typography>
        <Typography variant="subtitle2">{label}</Typography>
        {secondary && (
          <Typography variant="caption" sx={{ display: 'block', mt: 0.25 }}>
            {secondary}
          </Typography>
        )}
      </Box>
    </Wrapper>
  );
}

StatCard.propTypes = {
  label: PropTypes.string,
  value: PropTypes.any,
  secondary: PropTypes.any,
  variant: PropTypes.oneOf(['light', 'dark'])
};
