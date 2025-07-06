// src/components/AppGrid.jsx
import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material/styles';

function makeSpan(n) {
  return { gridColumn: `span ${n}` };        // <-- fixed
}

export default function AppGrid({ size = 'grow', sx, ...rest }) {
  const theme = useTheme();
  let style = {};

  if (size === 'grow') {
    style = { gridColumn: '1 / -1' };
  } else if (typeof size === 'number') {
    style = makeSpan(size);
  } else if (typeof size === 'object') {
    style = {};
    Object.entries(size).forEach(([bp, v]) => {
      style[theme.breakpoints.up(bp)] =
        v === 'grow' ? { gridColumn: '1 / -1' } : makeSpan(v);
    });
  }

  return <Grid sx={{ ...style, ...sx }} {...rest} />;
}
