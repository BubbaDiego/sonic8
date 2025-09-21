// Source-of-truth theme tokens. You can add new themes later (e.g., "midnight").
export const DEFAULT_TOKENS = {
  light: {
    base: 'light',
    bg: '#e7ecfa',       // component background.default
    page: '#e7ecfa',     // NEW: viewport/page background color
    surface: '#ffffff',
    card: '#f8fafc',
    text: '#222222',          // body text
    textTitle: '#111111',     // NEW: headings (h1-h6, Typography variants)
    primary: '#4678d8',
    wallpaper: 'none',
    useImage: false,      // NEW: toggle wallpaper image on/off
    font: 'Roboto',
    fontSize: 14,
    // NEW: themed card images
    cardUseImage: false,
    cardImage: 'none',
    // Wallpaper controls
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'scroll',
    wallpaperOverlay: 'none',
    // NEW: Border controls
    borderCard: '#FFFFFF22',
    borderCardWidth: 1,
    borderSurface: '#FFFFFF14',
    borderSurfaceWidth: 1,
    borderHeader: '#00000022',
    borderHeaderWidth: 0
  },
  dark: {
    base: 'dark',
    bg: '#0f172a',
    page: '#0b1220',
    surface: '#14161c',
    card: '#0b1220',
    text: '#e6e6e6',
    textTitle: '#ffffff',
    primary: '#4678d8',
    wallpaper: 'none',
    useImage: false,
    font: 'Roboto',
    fontSize: 14,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'fixed',
    wallpaperOverlay: 'none',
    borderCard: '#FFFFFF22',
    borderCardWidth: 1,
    borderSurface: '#FFFFFF14',
    borderSurfaceWidth: 1,
    borderHeader: '#00000033',
    borderHeaderWidth: 0
  },
  funky: {
    base: 'dark',
    bg: '#0e1731',
    page: '#0e1731',
    surface: '#101a3a',
    card: '#0e1b36',
    text: '#eae6ff',
    textTitle: '#ffffff',
    primary: '#8b5cf6',
    // You can point this to your mural, or leave 'none' and set in Theme Lab
    wallpaper: 'none',
    useImage: false,
    font: 'Roboto',
    fontSize: 14,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'fixed',
    wallpaperOverlay: 'none',
    borderCard: '#FFFFFF22',
    borderCardWidth: 1,
    borderSurface: '#FFFFFF14',
    borderSurfaceWidth: 1,
    borderHeader: '#00000033',
    borderHeaderWidth: 0
  }
};

const LS_KEY = (name) => `sonic:theme.tokens:${name}`;
const LS_PROFILES = `sonic:theme.profiles`; // JSON string: ["light","dark","funky",...]
const DEFAULT_PROFILES = ['light', 'dark', 'funky'];

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
  // Prefer direct bridge (fast, no event storms). Fallback to event.
  try {
    if (typeof window !== 'undefined' && typeof window.__sonicPreview === 'function') {
      window.__sonicPreview(name, tokens);
      return;
    }
  } catch {}
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('sonic-theme-preview', { detail: { name, tokens } }));
  }
}

export function clearPreview() {
  try {
    if (typeof window !== 'undefined' && typeof window.__sonicPreviewClear === 'function') {
      window.__sonicPreviewClear();
      return;
    }
  } catch {}
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('sonic-theme-preview-clear'));
  }
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

// ---------- Profile management ----------
function readProfiles() {
  try {
    const raw = localStorage.getItem(LS_PROFILES);
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length) return Array.from(new Set([...DEFAULT_PROFILES, ...arr]));
    }
  } catch {}
  return [...DEFAULT_PROFILES];
}
function writeProfiles(list) {
  const keep = list.filter(Boolean);
  localStorage.setItem(LS_PROFILES, JSON.stringify(keep));
  window.dispatchEvent(new Event('sonic-theme-updated'));
}

export function getProfiles() {
  return readProfiles();
}
export function addProfile(name, { base = 'dark', copyFrom = 'dark' } = {}) {
  if (!name) return;
  const profiles = readProfiles();
  if (profiles.includes(name)) return;
  const src = loadTokens(copyFrom);
  saveTokens(name, { ...src, base });
  writeProfiles([...profiles, name]);
}
export function renameProfile(oldName, newName) {
  if (!oldName || !newName || DEFAULT_PROFILES.includes(oldName)) return; // don't rename defaults
  const profiles = readProfiles();
  if (!profiles.includes(oldName)) return;
  const tokens = loadTokens(oldName);
  removeTokens(oldName);
  saveTokens(newName, tokens);
  writeProfiles(profiles.map((p) => (p === oldName ? newName : p)));
}
export function deleteProfile(name) {
  if (!name || DEFAULT_PROFILES.includes(name)) return; // protect defaults
  const profiles = readProfiles().filter((p) => p !== name);
  removeTokens(name);
  writeProfiles(profiles);
}
export function isDefaultProfile(name) {
  return DEFAULT_PROFILES.includes(name);
}
export function ensureProfilesInitialized() {
  writeProfiles(readProfiles());
}
