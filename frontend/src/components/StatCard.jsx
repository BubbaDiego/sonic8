import PropTypes from 'prop-types';
import { styled, alpha, useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import MainCard from 'ui-component/cards/MainCard';

/**
 * Unified statistic card for both Portfolio and Operations bars.
 * `variant` toggles between the original dark (blue) and light (white) looks.
 */
const CardWrapper = styled(MainCard, {
  shouldForwardProp: (prop) => prop !== 'variant'
})(({ theme, variant }) => {
  const dark = variant === 'dark';

  return {
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: dark ? theme.palette.primary.dark : '#fff',
    color: dark ? theme.palette.primary.light : theme.palette.text.primary,
    '&:after': {
      content: '""',
      position: 'absolute',
      width: 210,
      height: 210,
      background: `linear-gradient(210.04deg,
        ${dark ? theme.palette.primary[200] : theme.palette.primary.dark} -50.94%,
        rgba(144,202,249,0) 83.49%)`,
      borderRadius: '50%',
      top: -30,
      right: -180
    },
    '&:before': {
      content: '""',
      position: 'absolute',
      width: 210,
      height: 210,
      background: `linear-gradient(140.9deg,
        ${dark ? theme.palette.primary[200] : theme.palette.primary.dark} -14.02%,
        rgba(144,202,249,0) 77.58%)`,
      borderRadius: '50%',
      top: -160,
      right: -130
    }
  };
});

export default function StatCard({
  icon,
  label,
  value,
  secondary,
  variant = 'light',
  onClick
}) {
  const theme = useTheme();

  return (
    <CardWrapper
      variant={variant}
      border={false}
      content={false}
      onClick={onClick}
      sx={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        {icon && (
          <Avatar
            variant="rounded"
            sx={{
              ...theme.typography.commonAvatar,
              ...theme.typography.largeAvatar,
              bgcolor: variant === 'dark'
                ? 'primary.800'
                : alpha(theme.palette.primary.light, 1),
              color: variant === 'dark' ? '#fff' : 'primary.dark'
            }}
          >
            {icon}
          </Avatar>
        )}

        <Box sx={{ textAlign: 'left' }}>
          <Typography variant="h4">{value}</Typography>
          <Typography
            variant="subtitle2"
            sx={{ lineHeight: 1.1, mt: 0.25, opacity: 0.8 }}
          >
            {label}
          </Typography>
          {secondary && (
            <Typography
              variant="caption"
              sx={{ display: 'block', mt: 0.25, whiteSpace: 'nowrap' }}
            >
              {secondary}
            </Typography>
          )}
        </Box>
      </Box>
    </CardWrapper>
  );
}

StatCard.propTypes = {
  icon: PropTypes.node,
  label: PropTypes.string,
  value: PropTypes.any,
  secondary: PropTypes.any,
  variant: PropTypes.oneOf(['light', 'dark']),
  onClick: PropTypes.func
};