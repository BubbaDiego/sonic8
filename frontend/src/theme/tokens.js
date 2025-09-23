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
  },
  // =========================
  // NEW THEMES
  // =========================
  midnight: {
    // Deep, cool navy — crisp cyan accents
    base: 'dark',
    bg: '#0b1020',
    page: '#0b1220',
    surface: '#111827',
    card: '#0d1324',
    text: '#e5f0ff',
    textTitle: '#ffffff',
    primary: '#7dd3fc',               // sky-300
    wallpaper: 'none',
    useImage: false,
    font: 'Space Grotesk',
    fontSize: 14,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: '50% 35%',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'fixed',
    wallpaperOverlay: 'none',
    borderCard: '#9acbff33',
    borderCardWidth: 1,
    borderSurface: '#9acbff22',
    borderSurfaceWidth: 1,
    borderHeader: '#7dd3fc44',
    borderHeaderWidth: 1
  },
  miami_vice: {
    // Neon night: indigo canvas, hot pink primary, aqua highlights
    base: 'dark',
    bg: '#0a0d1a',
    page: '#0a0f24',
    surface: '#111730',
    card: '#0c142a',
    text: '#eafffb',
    textTitle: '#ffffff',
    primary: '#ff6ec7',               // neon pink
    wallpaper: 'none',
    useImage: false,
    font: 'Orbitron',
    fontSize: 15,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'fixed',
    wallpaperOverlay: 'linear-gradient(rgba(0,255,255,0.10), rgba(255,110,199,0.10))',
    borderCard: '#00e6ff3d',          // aqua edge
    borderCardWidth: 1,
    borderSurface: '#ff6ec733',
    borderSurfaceWidth: 1,
    borderHeader: '#00e6ff4d',
    borderHeaderWidth: 1
  },
  industrial: {
    // Utilitarian steel: neutral greys, subtle blue steel primary
    base: 'dark',
    bg: '#16181d',
    page: '#111317',
    surface: '#1f232b',
    card: '#1a1f27',
    text: '#e6e6e6',
    textTitle: '#ffffff',
    primary: '#9aa4b2',
    wallpaper: 'none',
    useImage: false,
    font: 'Inter',
    fontSize: 14,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'scroll',
    wallpaperOverlay: 'none',
    borderCard: '#9aa4b23b',
    borderCardWidth: 1,
    borderSurface: '#ffffff1f',
    borderSurfaceWidth: 1,
    borderHeader: '#ffffff24',
    borderHeaderWidth: 1
  },
  sunset: {
    // Warm dusk: soft creams & coral primary for a light, friendly UI
    base: 'light',
    bg: '#fff4e6',
    page: '#fff1dd',
    surface: '#ffffff',
    card: '#ffe8cc',
    text: '#45322e',
    textTitle: '#2c1f1b',
    primary: '#ff7a59',               // coral
    wallpaper: 'none',
    useImage: false,
    font: 'Poppins',
    fontSize: 14,
    cardUseImage: false,
    cardImage: 'none',
    wallpaperSize: 'cover',
    wallpaperPosition: 'center',
    wallpaperRepeat: 'no-repeat',
    wallpaperAttachment: 'scroll',
    wallpaperOverlay: 'linear-gradient(rgba(255,122,89,0.08), rgba(255,197,86,0.08))',
    borderCard: '#ff7a5933',
    borderCardWidth: 1,
    borderSurface: '#00000010',
    borderSurfaceWidth: 1,
    borderHeader: '#ff7a5940',
    borderHeaderWidth: 1
  }
};

const LS_KEY = (name) => `sonic:theme.tokens:${name}`;
const LS_PROFILES = `sonic:theme.profiles`; // JSON string: ["light","dark","funky",...]
// Include the new themes in the defaults so they appear immediately
const DEFAULT_PROFILES = ['light', 'dark', 'funky', 'midnight', 'miami_vice', 'industrial', 'sunset'];

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
