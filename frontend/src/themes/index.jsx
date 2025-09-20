import PropTypes from 'prop-types';
import { useMemo, useEffect, useState } from 'react';

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

  const [systemPrefersDark, setSystemPrefersDark] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  const resolvedMode = useMemo(() => {
    if (mode === ThemeMode.SYSTEM) {
      return systemPrefersDark ? ThemeMode.DARK : ThemeMode.LIGHT;
    }
    if (mode === ThemeMode.FUNKY) {
      return ThemeMode.DARK;
    }
    return mode;
  }, [mode, systemPrefersDark]);

  const theme = useMemo(() => Palette(resolvedMode, presetColor), [resolvedMode, presetColor]);

  const effectiveFontFamily = mode === ThemeMode.SYSTEM ? `'Roboto', sans-serif` : fontFamily;

  const themeTypography = useMemo(
    () => Typography(theme, borderRadius, effectiveFontFamily),
    [theme, borderRadius, effectiveFontFamily]
  );
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
  themes.components = useMemo(
    () => componentStyleOverrides(themes, borderRadius, outlinedFilled),
    [themes, borderRadius, outlinedFilled]
  );

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    const html = document.documentElement;
    if (!html) {
      return;
    }

    // Use resolved value so CSS and MUI agree.
    // Keep funky as its own CSS theme (MUI still uses dark palette via resolvedMode).
    const cssMode = mode === ThemeMode.FUNKY ? 'funky' : resolvedMode;
    html.dataset.theme = cssMode;
    html.style.setProperty('--asset-base', import.meta.env.BASE_URL);

    if (typeof window !== 'undefined' && window.localStorage) {
      const wallpaper = window.localStorage.getItem(`sonic:wallpaper:${cssMode}`);
      if (wallpaper) {
        html.style.setProperty('--body-bg-image', `url('${wallpaper}')`);
      } else {
        html.style.removeProperty('--body-bg-image');
      }

      try {
        const rawOverrides = window.localStorage.getItem(`sonic:theme.overrides:${cssMode}`);
        if (rawOverrides) {
          const overrides = JSON.parse(rawOverrides);
          Object.entries(overrides).forEach(([key, value]) => {
            html.style.setProperty(String(key), String(value));
          });
        }
      } catch (error) {
        // ignore malformed overrides
      }
    }
  }, [mode, resolvedMode]);

  useEffect(() => {
    if (mode !== ThemeMode.SYSTEM || typeof window === 'undefined') {
      return undefined;
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (event) => setSystemPrefersDark(event.matches);

    if (media.addEventListener) {
      media.addEventListener('change', listener);
    } else if (media.addListener) {
      media.addListener(listener);
    }

    return () => {
      if (media.removeEventListener) {
        media.removeEventListener('change', listener);
      } else if (media.removeListener) {
        media.removeListener(listener);
      }
    };
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
