import PropTypes from 'prop-types';
import { useMemo, useEffect } from 'react';

// material-ui
import { createTheme, StyledEngineProvider, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// project imports
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';
import Palette from './palette';
import Typography from './typography';

import componentStyleOverrides from './compStyleOverride';
import customShadows from './shadows';

export default function ThemeCustomization({ children }) {
  const { borderRadius, fontFamily, mode, outlinedFilled, presetColor, themeDirection } = useConfig();

  const resolvedMode = useMemo(() => {
    if (mode === ThemeMode.SYSTEM && typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? ThemeMode.DARK : ThemeMode.LIGHT;
    }
    return mode;
  }, [mode]);

  const theme = useMemo(() => Palette(resolvedMode, presetColor), [resolvedMode, presetColor]);

  const themeTypography = useMemo(() => Typography(theme, borderRadius, fontFamily), [theme, borderRadius, fontFamily]);
  const themeCustomShadows = useMemo(() => customShadows(resolvedMode, theme), [resolvedMode, theme]);


  const themeOptions = useMemo(
    () => ({
      direction: themeDirection,
      palette: theme.palette,
      mixins: {
        toolbar: {
          minHeight: '48px',
          padding: '16px',
          '@media (min-width: 600px)': {
            minHeight: '48px'
          }
        }
      },
      typography: themeTypography,
      customShadows: themeCustomShadows
    }),
    [themeDirection, theme, themeCustomShadows, themeTypography]
  );

  const themes = createTheme(themeOptions);
  themes.components = useMemo(() => componentStyleOverrides(themes, borderRadius, outlinedFilled), [themes, borderRadius, outlinedFilled]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
  }, [mode]);

  return (
    <StyledEngineProvider injectFirst>
      <ThemeProvider theme={themes}>
        <CssBaseline enableColorScheme />
        {children}
      </ThemeProvider>
    </StyledEngineProvider>
  );
}

ThemeCustomization.propTypes = { children: PropTypes.node };
