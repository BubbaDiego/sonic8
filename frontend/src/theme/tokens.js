// Source-of-truth theme tokens. You can add new themes later (e.g., "midnight").
export const DEFAULT_TOKENS = {
  light: {
    bg: '#e7ecfa',       // component background.default
    page: '#e7ecfa',     // NEW: viewport/page background color
    surface: '#ffffff',
    card: '#f8fafc',
    text: '#222222',
    primary: '#4678d8',
    wallpaper: 'none',
    useImage: false       // NEW: toggle wallpaper image on/off
  },
  dark: {
    bg: '#0f172a',
    page: '#0b1220',
    surface: '#14161c',
    card: '#0b1220',
    text: '#e6e6e6',
    primary: '#4678d8',
    wallpaper: 'none',
    useImage: false
  },
  funky: {
    bg: '#0e1731',
    page: '#0e1731',
    surface: '#101a3a',
    card: '#0e1b36',
    text: '#eae6ff',
    primary: '#8b5cf6',
    // You can point this to your mural, or leave 'none' and set in Theme Lab
    wallpaper: 'none',
    useImage: false
  }
};

const LS_KEY = (name) => `sonic:theme.tokens:${name}`;

export function loadTokens(name) {
  try {
    const base = DEFAULT_TOKENS[name] || DEFAULT_TOKENS.light;
    const raw = localStorage.getItem(LS_KEY(name));
    if (!raw) return base;
    const overrides = JSON.parse(raw);
    return { ...base, ...overrides };
  } catch {
    return DEFAULT_TOKENS[name] || DEFAULT_TOKENS.light;
  }
}

export function saveTokens(name, tokens) {
  localStorage.setItem(LS_KEY(name), JSON.stringify(tokens));
  window.dispatchEvent(new Event('sonic-theme-updated'));
}

export function removeTokens(name) {
  localStorage.removeItem(LS_KEY(name));
  window.dispatchEvent(new Event('sonic-theme-updated'));
}

export function exportAllThemes() {
  const names = Object.keys(DEFAULT_TOKENS);
  const bundle = {};
  names.forEach((n) => (bundle[n] = loadTokens(n)));
  return bundle;
}

export function importAllThemes(bundle) {
  Object.entries(bundle || {}).forEach(([name, tokens]) => {
    if (!DEFAULT_TOKENS[name]) return; // ignore unknown names for safety
    saveTokens(name, tokens);
  });
  window.dispatchEvent(new Event('sonic-theme-updated'));
}

// ------ Live Preview helpers (non-persistent) ------
export function previewTokens(name, tokens) {
  // tokens: partial override to preview immediately
  window.dispatchEvent(new CustomEvent('sonic-theme-preview', { detail: { name, tokens } }));
}

export function clearPreview() {
  window.dispatchEvent(new Event('sonic-theme-preview-clear'));
}

// Clear every theme override (useful when things feel "stuck")
export function resetAllThemeData() {
  try {
    Object.keys(DEFAULT_TOKENS).forEach((n) => {
      localStorage.removeItem(`sonic:theme.tokens:${n}`);
      localStorage.removeItem(`sonic:theme.overrides:${n}`);
      localStorage.removeItem(`sonic:wallpaper:${n}`);
    });
  } catch {}
  window.dispatchEvent(new Event('sonic-theme-updated'));
}
