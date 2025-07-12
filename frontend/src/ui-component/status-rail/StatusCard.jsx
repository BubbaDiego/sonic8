import PropTypes from 'prop-types';
import Box from '@mui/material/Box';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';

import './statusRail.scss';

/**
 * Generic flip‑card holding two faces.
 * `front` – { icon, color, label, value }
 * `back`  – ReactNode
 */
export default function StatusCard({ front, back, flipped, onToggle }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box className={flipped ? 'sr-card flipped' : 'sr-card'} onClick={onToggle}>
      <Box className="sr-inner">
        {/* Front – Portfolio view */}
        <Box className="sr-face sr-card--front">
          <Avatar
            variant="rounded"
            sx={{
              bgcolor: `${front.color}.main`,
              mb: 0.5,
              width: 32,
              height: 32
            }}
          >
            {front.icon}
          </Avatar>
          <Typography variant="h6">{front.value}</Typography>
          <Typography
            variant="caption"
            sx={{ opacity: 0.7, fontWeight: isDark ? 'bold' : 'normal', color: isDark ? '#fff' : 'inherit' }}
          >
            {front.label}
          </Typography>
        </Box>

        {/* Back – Monitor view */}
        <Box className="sr-face sr-face--back">{back}</Box>
      </Box>
    </Box>
  );
}

StatusCard.propTypes = {
  front: PropTypes.shape({
    icon: PropTypes.node,
    color: PropTypes.string,
    label: PropTypes.string,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
  }),
  back: PropTypes.node,
  flipped: PropTypes.bool,
  onToggle: PropTypes.func
};