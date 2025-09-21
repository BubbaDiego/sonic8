// Asset resolver: turn keys like "wallpaper.main" into full URLs.
// Supports theme variants ("light"/"dark"/"funky"), DPR ("2x"), and BASE_URL.
import manifest from '../assets/assets.manifest.json';

const BASE = (import.meta.env && import.meta.env.BASE_URL) ? String(import.meta.env.BASE_URL) : '/';
const join = (a, b) => `${a.replace(/\/+$/, '')}/${b.replace(/^\/+/, '')}`;

export function listAssetKeys(prefix = '') {
  const keys = Object.keys(manifest || {});
  return prefix ? keys.filter((k) => k.startsWith(prefix)) : keys;
}

export function resolveAsset(key, opts = {}) {
  const { theme, dpr = (typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1, absolute = false } = opts;
  const entry = (manifest && manifest[key]) || (manifest && manifest['images.missing']);
  const missing = join(BASE, '/images/missing.png');
  if (!entry) {
    if (absolute) {
      return typeof location !== 'undefined' ? location.origin + missing : missing;
    }
    return missing;
  }

  // theme variant -> default
  const variant = (theme && entry[theme]) || entry['default'] || Object.values(entry)[0];
  if (!variant) {
    if (absolute) {
      return typeof location !== 'undefined' ? location.origin + missing : missing;
    }
    return missing;
  }

  // DPR pick
  const src = (dpr >= 1.5 && entry['2x']?.src) ? entry['2x'].src : variant.src;
  const url = join(BASE, src);
  return absolute ? (typeof location !== 'undefined' ? location.origin + url : url) : url;
}

export function isAssetPointer(value) {
  return typeof value === 'string' && value.startsWith('asset:');
}

export function toAssetKey(value) {
  return isAssetPointer(value) ? value.slice(6) : null;
}
