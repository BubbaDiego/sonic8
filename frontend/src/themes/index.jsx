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
import { loadTokens } from '../theme/tokens';

// --- Font stacks + on-demand loader ---
const FONT_STACKS = {
  'System UI': "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
  Roboto: "'Roboto', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial",
  Inter: "'Inter', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial",
  Poppins: "'Poppins', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial",
  'Space Grotesk': "'Space Grotesk', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial",
  'JetBrains Mono': "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace"
};

const FONT_HREFS = {
  Roboto: 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap',
  Inter: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
  Poppins: 'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap',
  'Space Grotesk': 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap',
  'JetBrains Mono': 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap'
};

function ensureFontLoaded(name) {
  if (typeof document === 'undefined') return;
  const href = FONT_HREFS[name];
  if (!href) return;
  const id = `font-${name.replace(/\s+/g, '-').toLowerCase()}`;
  if (document.getElementById(id)) return;
  const link = document.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = href;
  document.head.appendChild(link);
}

// Normalize wallpaper path → absolute URL honoring BASE_URL
function normalizeWallpaperUrl(value) {
  if (!value || value === 'none') return null;
  if (value.startsWith('data:') || /^https?:\/\//i.test(value)) return value;
  const base = import.meta.env?.BASE_URL ? String(import.meta.env.BASE_URL) : '/';
  const join = (a, b) => a.replace(/\/+$/, '/') + b.replace(/^\/+/, '');
  return join(base, value);
}

export default function ThemeCustomization({ children }) {
  const { borderRadius, fontFamily, mode, outlinedFilled, presetColor, themeDirection } = useConfig();

  const [systemPrefersDark, setSystemPrefersDark] = useState(
    typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)').matches : false
  );
  const [themeVersion, setThemeVersion] = useState(0);
  const [preview, setPreview] = useState(null);

  const resolvedMode = useMemo(() => {
    if (mode === ThemeMode.SYSTEM) {
      return systemPrefersDark ? ThemeMode.DARK : ThemeMode.LIGHT;
    }
    if (mode === ThemeMode.FUNKY) {
      return ThemeMode.DARK;
    }
    return mode;
  }, [mode, systemPrefersDark]);

  const cssMode = useMemo(() => (mode === ThemeMode.FUNKY ? 'funky' : resolvedMode), [mode, resolvedMode]);
  const baseTokens = useMemo(() => loadTokens(cssMode), [cssMode, themeVersion]);
  const tokens = useMemo(
    () => (preview && preview.name === cssMode ? { ...baseTokens, ...preview.tokens } : baseTokens),
    [baseTokens, preview, cssMode]
  );

  const palette = useMemo(() => {
    const base = Palette(resolvedMode, presetColor).palette;
    return {
      ...base,
      mode: resolvedMode === ThemeMode.DARK ? 'dark' : 'light',
      primary: {
        ...base.primary,
        main: tokens.primary
      },
      background: {
        ...base.background,
        default: tokens.bg,
        paper: tokens.surface
      },
      text: {
        ...base.text,
        primary: tokens.text
      }
    };
  }, [resolvedMode, presetColor, tokens]);

  const baseTheme = useMemo(() => createTheme({ palette }), [palette]);
  const effectiveFontFamily = useMemo(
    () => (tokens.font ? FONT_STACKS[tokens.font] || fontFamily : fontFamily),
    [tokens.font, fontFamily]
  );
  const themeTypography = useMemo(
    () => Typography(baseTheme, borderRadius, effectiveFontFamily),
    [baseTheme, borderRadius, effectiveFontFamily]
  );
  const themeCustomShadows = useMemo(() => customShadows(resolvedMode, baseTheme), [resolvedMode, baseTheme]);

  const themeOptions = useMemo(
    () => ({
      direction: themeDirection,
      palette,
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
    [themeDirection, palette, themeTypography, themeCustomShadows]
  );

  const themes = useMemo(() => createTheme(themeOptions), [themeOptions]);
  const components = useMemo(
    () => componentStyleOverrides(themes, borderRadius, outlinedFilled),
    [themes, borderRadius, outlinedFilled]
  );
  themes.components = components;
  themes.applyStyles =
    themes.applyStyles || ((targetMode, styles) => (themes.palette.mode === targetMode ? styles : {}));

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    const html = document.documentElement;
    if (!html) {
      return;
    }

    html.dataset.theme = cssMode;
    html.style.setProperty('--asset-base', import.meta.env.BASE_URL);

    const setVar = (key, value) => {
      if (value != null && value !== '') {
        html.style.setProperty(key, String(value));
      } else {
        html.style.removeProperty(key);
      }
    };

    setVar('--bg', tokens.bg);
    setVar('--page', tokens.page ?? tokens.bg);
    setVar('--surface', tokens.surface);
    setVar('--card', tokens.card || tokens.surface);
    setVar('--text', tokens.text);
    setVar('--primary', tokens.primary);

    const wallpaperUrl = tokens.useImage ? normalizeWallpaperUrl(tokens.wallpaper) : null;
    if (wallpaperUrl) {
      setVar('--body-bg-image', `url('${wallpaperUrl}')`);
    } else {
      html.style.removeProperty('--body-bg-image');
    }

    const chosenFont = tokens.font || 'System UI';
    ensureFontLoaded(chosenFont);
    const stack = FONT_STACKS[chosenFont] || FONT_STACKS['System UI'];
    setVar('--font-ui', stack);
  }, [cssMode, tokens]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const bump = () => setThemeVersion((v) => v + 1);
    const storageHandler = () => bump();
    const themeEvt = () => bump();
    const onPreview = (event) => {
      const detail = event.detail || {};
      setPreview({ name: detail.name, tokens: detail.tokens || {} });
    };
    const onPreviewClear = () => setPreview(null);

    window.addEventListener('sonic-theme-updated', themeEvt);
    window.addEventListener('storage', storageHandler);
    window.addEventListener('sonic-theme-preview', onPreview);
    window.addEventListener('sonic-theme-preview-clear', onPreviewClear);

    const mql = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    const handler = (event) => setSystemPrefersDark(event.matches);

    if (mql) {
      if (mql.addEventListener) {
        mql.addEventListener('change', handler);
      } else if (mql.addListener) {
        mql.addListener(handler);
      }
    }

    return () => {
      window.removeEventListener('sonic-theme-updated', themeEvt);
      window.removeEventListener('storage', storageHandler);
      window.removeEventListener('sonic-theme-preview', onPreview);
      window.removeEventListener('sonic-theme-preview-clear', onPreviewClear);

      if (mql) {
        if (mql.removeEventListener) {
          mql.removeEventListener('change', handler);
        } else if (mql.removeListener) {
          mql.removeListener(handler);
        }
      }
    };
  }, []);

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
