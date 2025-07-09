
import PropTypes from 'prop-types';
import { styled } from '@mui/material/styles';
import MainCard from 'ui-component/cards/MainCard';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

const CardWrapper = styled(MainCard)(({ theme }) => ({
  backgroundColor: theme.palette.warning.light,
  color: theme.palette.warning.dark,
  overflow: 'hidden',
  position: 'relative'
}));

export default function TotalValueLightCard({ value, label = 'Total Value' }) {
  return (
    <CardWrapper>
      <Box sx={{ p: 2 }}>
        <Typography variant="h4">{value}</Typography>
        <Typography variant="subtitle2">{label}</Typography>
      </Box>
    </CardWrapper>
  );
}

TotalValueLightCard.propTypes = {
  value: PropTypes.any,
  label: PropTypes.string
};
