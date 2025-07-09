
import PropTypes from 'prop-types';
import { styled, useTheme } from '@mui/material/styles';
import MainCard from 'ui-component/cards/MainCard';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

const CardWrapper = styled(MainCard)(({ theme }) => ({
  backgroundColor: theme.palette.primary.dark,
  color: theme.palette.primary.light,
  overflow: 'hidden',
  position: 'relative'
}));

export default function TotalValueDarkCard({ value, label = 'Value' }) {
  const theme = useTheme();
  return (
    <CardWrapper>
      <Box sx={{ p: 2 }}>
        <Typography variant="h4">{value}</Typography>
        <Typography variant="subtitle2">{label}</Typography>
      </Box>
    </CardWrapper>
  );
}

TotalValueDarkCard.propTypes = {
  value: PropTypes.any,
  label: PropTypes.string
};
