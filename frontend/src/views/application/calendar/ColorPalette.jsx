import PropTypes from 'prop-types';
// material-ui
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';

// ==============================|| CALENDAR COLOR PALETTE ||============================== //

export default function ColorPalette({ color, label, value }) {
  return (
    <FormControlLabel
      value={value}
      control={<Radio sx={{ color, '&.Mui-checked': { color } }} />}
      label={label || ''}
      sx={{ pr: label ? 1 : 0 }}
    />
  );
}

ColorPalette.propTypes = { color: PropTypes.any, label: PropTypes.any, value: PropTypes.any };
