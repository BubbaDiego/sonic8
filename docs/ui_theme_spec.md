# User Interface Theme Specification
**Updated:** 2025-07-25

This document explains how the frontend switches between the supported color themes and lists all relevant files.

## Overview
The React application defines four modes via `ThemeMode`:
- `light`
- `dark`
- `funky`
- `system`

The default mode is `system`. The setting persists in `localStorage` and is exposed through `ConfigContext`.

## Key Files

### Configuration
- `frontend/src/config.js` – declares the `ThemeMode` enum and default options:

```javascript
export let ThemeMode;
(function (ThemeMode) {
  ThemeMode['LIGHT'] = 'light';
  ThemeMode['DARK'] = 'dark';
  ThemeMode['FUNKY'] = 'funky';
  ThemeMode['SYSTEM'] = 'system';
})(ThemeMode || (ThemeMode = {}));

const config = {
  menuOrientation: MenuOrientation.VERTICAL,
  miniDrawer: false,
  sidePanelWidth: 260,
  fontFamily: `'Roboto', sans-serif`,
  borderRadius: 8,
  outlinedFilled: true,
  mode: ThemeMode.SYSTEM,
  sidePanelWidth: 320,
  presetColor: 'default',
  i18n: 'en',
  themeDirection: ThemeDirection.LTR,
  container: true,
  cycloneRefreshDelay: CYCLONE_REFRESH_DELAY_MS
};
```

### Context and Hooks
- `frontend/src/contexts/ConfigContext.jsx` stores the user's chosen `mode` and other settings using `useLocalStorage`.
- `frontend/src/hooks/useConfig.js` exposes the context values to components.

### Theme Provider
- `frontend/src/themes/index.jsx` wraps the app with a Material UI `ThemeProvider` and applies CSS overrides. It also writes the current mode to `<html data-theme="...">` so the SCSS variables take effect.

### Palette and Typography
- `frontend/src/themes/palette.jsx` builds a Material UI palette using one of the SCSS modules (`_theme1.module.scss` … `_theme6.module.scss`) selected by `presetColor`.
- `frontend/src/themes/typography.jsx` and `frontend/src/themes/shadows.jsx` derive font and shadow values based on the palette and `ThemeMode`.

### CSS Variables
- `frontend/src/assets/scss/_sonic-themes.scss` defines CSS variables for each theme. The compiled version lives under `frontend/src/hedge-report/styles/sonic_themes.css`.
- Example snippet:

```css
:root[data-theme="funky"] {
  --bg: #1e1e40;
  --text: #fff;
  --body-bg-image: url('/images/trader_wallpaper.jpg');
  --section-bg-image: url('/images/wally2.png');
}
```

### UI Components
- `frontend/src/layout/MainLayout/Header/ThemeModeSection/index.jsx` cycles through the modes when the avatar is clicked.
- `frontend/src/layout/Customization/ThemeMode.jsx` provides radio buttons for explicit selection.
- `frontend/src/layout/Customization/PresetColor.jsx` lets the user pick one of the six color presets mentioned above.

## Runtime Flow
1. The initial mode is loaded from `localStorage` via `ConfigContext`.
2. `ThemeCustomization` applies the palette and sets `document.documentElement.dataset.theme` accordingly.
3. CSS rules in `_sonic-themes.scss` respond to this attribute, updating backgrounds and colours.
4. When the user toggles the theme (`ThemeModeSection`) or selects a preset, `onChangeMode`/`onChangePresetColor` update the context which triggers a re-render.

## File Map Summary
```
frontend/src/config.js
frontend/src/contexts/ConfigContext.jsx
frontend/src/hooks/useConfig.js
frontend/src/themes/index.jsx
frontend/src/themes/palette.jsx
frontend/src/themes/typography.jsx
frontend/src/themes/shadows.jsx
frontend/src/layout/MainLayout/Header/ThemeModeSection/index.jsx
frontend/src/layout/Customization/ThemeMode.jsx
frontend/src/layout/Customization/PresetColor.jsx
frontend/src/assets/scss/_themes-vars.module.scss
frontend/src/assets/scss/_theme1.module.scss ... _theme6.module.scss
frontend/src/assets/scss/_sonic-themes.scss
frontend/src/hedge-report/styles/sonic_themes.css
```

These files collectively implement theme selection and allow new colour packs or modes to be added with minimal changes.
