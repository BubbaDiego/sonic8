import React from 'react';
import { CircularProgress, Box, Tooltip, Typography, IconButton } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import NotificationsPausedIcon from '@mui/icons-material/NotificationsPaused';

/**
 * DonutCountdown
 * ---------------
 * Reusable radial countdown component with optional completion icon.
 *
 * Props:
 *  - remaining   : number (seconds left)
 *  - total       : number (total seconds for full circle)
 *  - label       : string (static label underneath ring)
 *  - paletteKey  : MUI palette key ('success' | 'warning' | etc.)
 *  - size        : number (diameter in px, default 48)
 *  - thickness   : number (stroke width, default 4)
 *  - onClick     : function (optional click handler, e.g. to open a pop‑over)
 */
function DonutCountdown({
  remaining,
  total,
  label,
  paletteKey = 'primary',
  size = 48,
  thickness = 4,
  onClick,
}) {
  const pct = Math.max(0, Math.min(100, (remaining / total) * 100));
  const finished = remaining <= 0;

  return (
    <Tooltip
      title={finished ? `${label}: completed` : `${label}: ${Math.floor(remaining)}s`}
      arrow
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <IconButton
          onClick={onClick}
          sx={{ p: 0, borderRadius: '50%', overflow: 'visible' }}
          disableRipple
        >
          <Box sx={{ position: 'relative', width: size, height: size }}>
            {/* background track */}
            <CircularProgress
              variant="determinate"
              value={100}
              size={size}
              thickness={thickness}
              sx={{
                color: (theme) => theme.palette.grey[800],
                opacity: 0.25,
                position: 'absolute',
                top: 0,
                left: 0,
              }}
            />
            {/* progress or completion icon */}
            {!finished ? (
              <>
                <CircularProgress
                  variant="determinate"
                  value={pct}
                  size={size}
                  thickness={thickness}
                  sx={{
                    color: (theme) => theme.palette[paletteKey].main,
                    position: 'absolute',
                    top: 0,
                    left: 0,
                  }}
                />
                <Box
                  sx={{
                    inset: 0,
                    position: 'absolute',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.7rem',
                    fontWeight: 500,
                    pointerEvents: 'none',
                  }}
                >
                  {Math.floor(remaining)}
                </Box>
              </>
            ) : (
              <Box
                sx={{
                  inset: 0,
                  position: 'absolute',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: (theme) => theme.palette[paletteKey].main,
                }}
              >
                {paletteKey === 'warning' ? (
                  <NotificationsPausedIcon fontSize="small" />
                ) : (
                  <CheckCircleIcon fontSize="small" />
                )}
              </Box>
            )}
          </Box>
        </IconButton>
        <Typography variant="caption" sx={{ mt: 0.25, userSelect: 'none' }}>
          {label}
        </Typography>
      </Box>
    </Tooltip>
  );
}

export default DonutCountdown;
