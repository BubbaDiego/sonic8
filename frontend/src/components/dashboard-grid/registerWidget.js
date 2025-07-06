import Grid from '@mui/material/Grid';

export default function AppGrid({ size = 'grow', ...rest }) {
  // 1. Extract breakpoints or single value
  const translate = (val) => {
    if (val === 'grow') return { xs: true, sx: { flexGrow: 1, flexBasis: 0 } };
    if (typeof val === 'number') return { xs: val };
    if (typeof val === 'object') {
      return Object.fromEntries(
        Object.entries(val).map(([bp, v]) =>
          v === 'grow' ? [bp, true] : [bp, v]
        )
      );
    }
    return {};
  };

  const { xs, sm, md, lg, xl, sx: growSx } = translate(size);

  return (
    <Grid
      item
      xs={xs}
      sm={sm}
      md={md}
      lg={lg}
      xl={xl}
      sx={growSx}
      {...rest}
    />
  );
}
