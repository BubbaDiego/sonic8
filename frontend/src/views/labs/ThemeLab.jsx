import { useMemo, useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Slider,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography
} from '@mui/material';
import {
  DEFAULT_TOKENS,
  loadTokens,
  saveTokens,
  removeTokens,
  exportAllThemes,
  importAllThemes,
  previewTokens,
  clearPreview,
  resetAllThemeData
} from '../../theme/tokens';
import { resolveAsset, isAssetPointer, toAssetKey, listAssetKeys } from '../../lib/assetsResolver';
import Autocomplete from '@mui/material/Autocomplete';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import UploadIcon from '@mui/icons-material/Upload';
import IconButton from '@mui/material/IconButton';

const THEME_NAMES = ['light', 'dark', 'funky'];
const FONT_OPTIONS = ['System UI', 'Roboto', 'Inter', 'Poppins', 'Space Grotesk', 'Orbitron', 'Neuropol', 'JetBrains Mono'];
const ColorInput = ({ label, value, onChange }) => (
  <Stack direction="row" alignItems="center" spacing={2}>
    <Typography sx={{ minWidth: 120 }}>{label}</Typography>
    <input
      type="color"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: 48, height: 32, border: 'none', background: 'transparent' }}
    />
    <TextField size="small" value={value} onChange={(e) => onChange(e.target.value)} sx={{ width: 160 }} />
  </Stack>
);

const SIZE_OPTS = ['cover', 'contain', '100% 100%', 'auto'];
const REPEAT_OPTS = ['no-repeat', 'repeat', 'repeat-x', 'repeat-y'];
const ATTACH_OPTS = ['fixed', 'scroll'];
const POS_PRESETS = ['center', 'top', 'bottom', 'left', 'right', 'custom'];
const SIMPLE_OVERLAY_RE = /linear-gradient\(rgba\((\d+),(\d+),(\d+),([\d.]+)\),\s*rgba\(\1,\2,\3,\4\)\)/i;

function parseXY(pos) {
  const match = String(pos || '').match(/^(\d{1,3})%\s+(\d{1,3})%$/);
  if (!match) return [50, 50];
  const clamp = (value) => Math.max(0, Math.min(100, Number(value)));
  return [clamp(match[1]), clamp(match[2])];
}

function hexToRgb(hex) {
  const normalized = hex.replace('#', '');
  const expanded =
    normalized.length === 3
      ? normalized
          .split('')
          .map((c) => c + c)
          .join('')
      : normalized;
  const bigint = parseInt(expanded, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function rgbToHex(r, g, b) {
  const toHex = (value) => value.toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function parseSimpleOverlay(value) {
  const match = SIMPLE_OVERLAY_RE.exec(String(value || ''));
  if (!match) return null;
  const [, r, g, b, alpha] = match;
  return { color: rgbToHex(Number(r), Number(g), Number(b)), alpha: Number(alpha) };
}

export default function ThemeLab() {
  const initialTokensRef = useRef(loadTokens('dark'));
  const initialTokens = initialTokensRef.current;
  const [name, setName] = useState('dark');
  const [state, setState] = useState(() => initialTokens);
  const [livePreview, setLivePreview] = useState(true);
  const [wallThumb, setWallThumb] = useState({ url: '', ok: null, loading: false });
  const [cardThumb, setCardThumb] = useState({ url: '', ok: null, loading: false });
  const [useWallAsset, setUseWallAsset] = useState(isAssetPointer(initialTokens.wallpaper));
  const [wallKey, setWallKey] = useState(() => (isAssetPointer(initialTokens.wallpaper) ? toAssetKey(initialTokens.wallpaper) : ''));
  const [useCardAsset, setUseCardAsset] = useState(isAssetPointer(initialTokens.cardImage));
  const [cardKey, setCardKey] = useState(() => (isAssetPointer(initialTokens.cardImage) ? toAssetKey(initialTokens.cardImage) : ''));
  const initialPosition = initialTokens.wallpaperPosition ?? 'center';
  const [xy, setXy] = useState(() => parseXY(initialPosition));
  const [posPreset, setPosPreset] = useState(() => (POS_PRESETS.includes(initialPosition) ? initialPosition : 'custom'));
  const initialOverlay = parseSimpleOverlay(initialTokens.wallpaperOverlay);
  const [overlayColor, setOverlayColor] = useState(initialOverlay ? initialOverlay.color : '#000000');
  const [overlayAlpha, setOverlayAlpha] = useState(initialOverlay ? initialOverlay.alpha : 0);
  const [simpleOverlayActive, setSimpleOverlayActive] = useState(Boolean(initialOverlay));
  const wallKeys = useMemo(() => listAssetKeys('wallpaper.'), []);
  const cardKeys = useMemo(() => listAssetKeys('cards.'), []);

  const base = useMemo(() => DEFAULT_TOKENS[name], [name]);

  const applyState = (next) => {
    setState(next);
    const wallPtr = isAssetPointer(next.wallpaper);
    setUseWallAsset(wallPtr);
    setWallKey(wallPtr ? toAssetKey(next.wallpaper) || '' : '');
    const cardPtr = isAssetPointer(next.cardImage);
    setUseCardAsset(cardPtr);
    setCardKey(cardPtr ? toAssetKey(next.cardImage) || '' : '');
  };

  const setField = (k, v) => {
    setState((s) => {
      const same = s[k] === v;
      const next = same ? s : { ...s, [k]: v };
      if (k === 'wallpaper') {
        const ptr = isAssetPointer(v);
        if (ptr) {
          setUseWallAsset(true);
          setWallKey(toAssetKey(v) || '');
        } else if (!useWallAsset) {
          setWallKey('');
        }
      }
      if (k === 'cardImage') {
        const ptr = isAssetPointer(v);
        if (ptr) {
          setUseCardAsset(true);
          setCardKey(toAssetKey(v) || '');
        } else if (!useCardAsset) {
          setCardKey('');
        }
      }
      return next;
    });
  };
  const resetToDefaults = () => applyState({ ...base });
  const save = () => {
    saveTokens(name, state); // fires 'sonic-theme-updated'
    try {
      if (typeof window !== 'undefined' && typeof window.__sonicPreviewClear === 'function') {
        window.__sonicPreviewClear();
      } else {
        clearPreview();
      }
    } catch {
      clearPreview();
    }
  };
  const remove = () => {
    removeTokens(name);
    const fresh = loadTokens(name);
    applyState(fresh);
    if (livePreview) previewTokens(name, fresh);
  };
  const discard = () => {
    const fresh = loadTokens(name);
    applyState(fresh);
    clearPreview();
  };
  const doExport = () => {
    const data = exportAllThemes();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sonic-themes.json';
    a.click();
    URL.revokeObjectURL(url);
  };
  const doImport = async (evt) => {
    const file = evt.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    try {
      importAllThemes(JSON.parse(text));
      const fresh = loadTokens(name);
      applyState(fresh);
      if (livePreview) previewTokens(name, fresh);
    } catch {
      alert('Invalid JSON');
    }
  };

  // Live preview current edits in context (debounced; uses direct bridge when available)
  const previewTimer = useRef(null);
  useEffect(() => {
    if (!livePreview) return;
    if (previewTimer.current) clearTimeout(previewTimer.current);
    const snapshotName = name;
    const snapshotState = state;
    previewTimer.current = setTimeout(() => {
      try {
        if (typeof window !== 'undefined' && typeof window.__sonicPreview === 'function') {
          window.__sonicPreview(snapshotName, snapshotState);
        } else {
          previewTokens(snapshotName, snapshotState);
        }
      } catch {
        previewTokens(snapshotName, snapshotState);
      }
    }, 150); // ~6-7 updates/sec while dragging
    return () => {
      if (previewTimer.current) clearTimeout(previewTimer.current);
    };
  }, [name, state, livePreview]);

  useEffect(() => () => clearPreview(), []);

  useEffect(() => {
    const rawPosition = state.wallpaperPosition ?? 'center';
    const preset = POS_PRESETS.includes(rawPosition) ? rawPosition : 'custom';
    setPosPreset(preset);
    if (preset === 'custom') {
      setXy(parseXY(rawPosition));
    }
  }, [state.wallpaperPosition]);

  useEffect(() => {
    const parsed = parseSimpleOverlay(state.wallpaperOverlay);
    if (parsed) {
      setSimpleOverlayActive(true);
      setOverlayColor((prev) => (prev.toLowerCase() === parsed.color.toLowerCase() ? prev : parsed.color));
      setOverlayAlpha((prev) => (Math.abs(prev - parsed.alpha) < 0.0001 ? prev : parsed.alpha));
    } else {
      setSimpleOverlayActive(false);
      setOverlayAlpha((prev) => (prev === 0 ? prev : 0));
    }
  }, [state.wallpaperOverlay]);

  useEffect(() => {
    if (posPreset === 'custom') {
      const value = `${xy[0]}% ${xy[1]}%`;
      setField('wallpaperPosition', value);
    } else {
      setField('wallpaperPosition', posPreset);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [posPreset, xy]);

  useEffect(() => {
    if (!simpleOverlayActive) return;
    if (overlayAlpha <= 0) {
      setField('wallpaperOverlay', 'none');
      return;
    }
    const [r, g, b] = hexToRgb(overlayColor);
    const css = `linear-gradient(rgba(${r},${g},${b},${overlayAlpha}), rgba(${r},${g},${b},${overlayAlpha}))`;
    setField('wallpaperOverlay', css);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simpleOverlayActive, overlayAlpha, overlayColor]);

  useEffect(() => {
    let v = state.wallpaper;
    if (useWallAsset) v = wallKey ? `asset:${wallKey}` : 'none';
    if (!state.useImage || !v || v === 'none') {
      setWallThumb({ url: '', ok: null, loading: false });
      return;
    }
    const base = import.meta.env?.BASE_URL ? String(import.meta.env.BASE_URL) : '/';
    const normalize = (value) => {
      if (value.startsWith('data:') || /^https?:\/\//i.test(value)) return value;
      return `${location.origin}${base.replace(/\/$/, '')}/${value.replace(/^\//, '')}`;
    };
    const url = isAssetPointer(v) ? resolveAsset(toAssetKey(v), { theme: name, absolute: true }) : normalize(v);
    setWallThumb({ url, ok: null, loading: true });
    const img = new Image();
    img.onload = () => setWallThumb({ url, ok: true, loading: false });
    img.onerror = () => setWallThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.wallpaper, state.useImage, useWallAsset, wallKey, name]);

  // Card image thumbnail + validation
  useEffect(() => {
    let v = state.cardImage;
    if (useCardAsset) v = cardKey ? `asset:${cardKey}` : 'none';
    if (!state.cardUseImage || !v || v === 'none') {
      setCardThumb({ url: '', ok: null, loading: false });
      return;
    }
    const base = import.meta.env?.BASE_URL ? String(import.meta.env.BASE_URL) : '/';
    const normalize = (value) => {
      if (value.startsWith('data:') || /^https?:\/\//i.test(value)) return value;
      return `${location.origin}${base.replace(/\/$/, '')}/${value.replace(/^\//, '')}`;
    };
    const url = isAssetPointer(v) ? resolveAsset(toAssetKey(v), { theme: name, absolute: true }) : normalize(v);
    setCardThumb({ url, ok: null, loading: true });
    const img = new Image();
    img.onload = () => setCardThumb({ url, ok: true, loading: false });
    img.onerror = () => setCardThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.cardImage, state.cardUseImage, useCardAsset, cardKey, name]);

  const uploadToField =
    (fieldName, extra = {}, onLoad) =>
    async (evt) => {
      const file = evt.target?.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof onLoad === 'function') {
          onLoad();
        }
        setField(fieldName, reader.result);
        Object.entries(extra).forEach(([key, value]) => setField(key, value));
      };
      reader.readAsDataURL(file);
      evt.target.value = '';
    };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Theme Lab
      </Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>
        Edit fonts, backgrounds, and panel colors per theme. Live preview on; save when you like it.
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: 'wrap' }}>
              <Tooltip title="The UI mode currently applied by the header toggle">
                <Chip size="small" label={`Active UI Mode: ${document.documentElement.dataset.theme || 'unknown'}`} />
              </Tooltip>
              <Tooltip title="The theme you are editing">
                <Chip size="small" color="primary" variant="outlined" label={`Editing: ${name}`} />
              </Tooltip>
              {document.documentElement.dataset.theme !== name && <Chip size="small" color="warning" label="Note: editing ≠ active" />}
              <Box sx={{ flexGrow: 1 }} />
              <Typography sx={{ mr: 1 }}>Theme</Typography>
              <TextField
                select
                size="small"
                value={name}
                onChange={(e) => {
                  const n = e.target.value;
                  const next = loadTokens(n);
                  setName(n);
                  applyState(next);
                }}
              >
                {THEME_NAMES.map((n) => (
                  <MenuItem key={n} value={n}>
                    {n}
                  </MenuItem>
                ))}
              </TextField>
              <FormControlLabel control={<Switch checked={livePreview} onChange={(e) => setLivePreview(e.target.checked)} />} label="Live Preview" />
            </Stack>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: 'wrap' }}>
              <Button variant="outlined" onClick={resetToDefaults}>
                Revert To Defaults
              </Button>
              <Button variant="contained" onClick={save}>
                Save & Apply
              </Button>
              <Button color="error" onClick={remove}>
                Remove Override
              </Button>
              <Button onClick={discard}>Discard Unsaved</Button>
              <Button
                onClick={() => {
                  resetAllThemeData();
                  applyState(loadTokens(name));
                }}
                title="Clears all saved theme data for all themes"
              >
                Reset All
              </Button>
              <Box sx={{ flexGrow: 1 }} />
              <Button variant="outlined" onClick={doExport}>
                Export JSON
              </Button>
              <Button component="label" variant="outlined">
                Import JSON
                <input hidden type="file" accept="application/json" onChange={doImport} />
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Text" />
            <CardContent>
              <Stack spacing={2}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 80 }}>Font</Typography>
                  <TextField select size="small" value={state.font || 'System UI'} onChange={(e) => setField('font', e.target.value)} sx={{ width: 220 }}>
                    {FONT_OPTIONS.map((font) => (
                      <MenuItem key={font} value={font}>
                        {font}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Stack spacing={1}>
                  <Typography variant="caption">Font size (px)</Typography>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Slider
                      value={Number(state.fontSize || 14)}
                      min={11}
                      max={20}
                      step={1}
                      onChange={(_, value) => {
                        const raw = Array.isArray(value) ? value[0] : value;
                        setField('fontSize', Number(raw));
                      }}
                      sx={{ width: 180 }}
                    />
                    <TextField
                      size="small"
                      type="number"
                      sx={{ width: 90 }}
                      value={Number(state.fontSize || 14)}
                      onChange={(e) => {
                        const parsed = Number(e.target.value || 14);
                        const clamped = Number.isFinite(parsed) ? Math.max(10, Math.min(24, parsed)) : 14;
                        setField('fontSize', clamped);
                      }}
                    />
                  </Stack>
                </Stack>
                <ColorInput label="Body text (--text)" value={state.text} onChange={(v) => setField('text', v)} />
                <ColorInput
                  label="Heading text (--text-title)"
                  value={state.textTitle ?? state.text}
                  onChange={(v) => setField('textTitle', v)}
                />
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Live text preview
                </Typography>
                <Typography variant="h4" gutterBottom>
                  Heading 4 uses --text-title
                </Typography>
                <Typography variant="body2">
                  The quick brown fox jumps over the lazy dog — 1234567890 (body uses --text).
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Borders" />
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Card borders
                </Typography>
                <Stack spacing={1}>
                  <Typography variant="caption">Card border width (px)</Typography>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Slider
                      value={Number(state.borderCardWidth ?? 0)}
                      min={0}
                      max={8}
                      step={1}
                      onChange={(_, value) => {
                        const raw = Array.isArray(value) ? value[0] : value;
                        setField('borderCardWidth', Number(raw));
                      }}
                      sx={{ width: 180 }}
                    />
                    <TextField
                      size="small"
                      type="number"
                      sx={{ width: 90 }}
                      value={Number(state.borderCardWidth ?? 0)}
                      onChange={(e) =>
                        setField('borderCardWidth', Math.max(0, Math.min(12, Number(e.target.value || 0))))
                      }
                    />
                  </Stack>
                  <ColorInput
                    label="Color (--border-card)"
                    value={state.borderCard || '#00000000'}
                    onChange={(v) => setField('borderCard', v)}
                  />
                </Stack>
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Surface/Container borders
                </Typography>
                <Stack spacing={1}>
                  <Typography variant="caption">Surface/Container border width (px)</Typography>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Slider
                      value={Number(state.borderSurfaceWidth ?? 0)}
                      min={0}
                      max={8}
                      step={1}
                      onChange={(_, value) => {
                        const raw = Array.isArray(value) ? value[0] : value;
                        setField('borderSurfaceWidth', Number(raw));
                      }}
                      sx={{ width: 180 }}
                    />
                    <TextField
                      size="small"
                      type="number"
                      sx={{ width: 90 }}
                      value={Number(state.borderSurfaceWidth ?? 0)}
                      onChange={(e) =>
                        setField('borderSurfaceWidth', Math.max(0, Math.min(12, Number(e.target.value || 0))))
                      }
                    />
                  </Stack>
                  <ColorInput
                    label="Color (--border-surface)"
                    value={state.borderSurface || '#00000000'}
                    onChange={(v) => setField('borderSurface', v)}
                  />
                </Stack>
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Header/menu separator
                </Typography>
                <Stack spacing={1}>
                  <Typography variant="caption">Header separator width (px)</Typography>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Slider
                      value={Number(state.borderHeaderWidth ?? 0)}
                      min={0}
                      max={8}
                      step={1}
                      onChange={(_, value) => {
                        const raw = Array.isArray(value) ? value[0] : value;
                        setField('borderHeaderWidth', Number(raw));
                      }}
                      sx={{ width: 180 }}
                    />
                    <TextField
                      size="small"
                      type="number"
                      sx={{ width: 90 }}
                      value={Number(state.borderHeaderWidth ?? 0)}
                      onChange={(e) =>
                        setField('borderHeaderWidth', Math.max(0, Math.min(12, Number(e.target.value || 0))))
                      }
                    />
                  </Stack>
                  <ColorInput
                    label="Color (--border-header)"
                    value={state.borderHeader || '#00000000'}
                    onChange={(v) => setField('borderHeader', v)}
                  />
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>



        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Panels" />
            <CardContent>
              <Stack spacing={2}>
                <ColorInput label="Background (--bg)" value={state.bg} onChange={(v) => setField('bg', v)} />
                <ColorInput label="Surface / Paper (--surface)" value={state.surface} onChange={(v) => setField('surface', v)} />
                <ColorInput label="Card (--card)" value={state.card} onChange={(v) => setField('card', v)} />
                <ColorInput label="Primary (--primary)" value={state.primary} onChange={(v) => setField('primary', v)} />
                <Divider />
                <FormControlLabel
                  control={<Switch checked={!!state.cardUseImage} onChange={(e) => setField('cardUseImage', e.target.checked)} />}
                  label="Use Card Image"
                />
                <Stack spacing={1}>
                  <FormControlLabel
                    control={(
                      <Switch
                        checked={useCardAsset}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setUseCardAsset(checked);
                          if (checked) {
                            const first = cardKeys[0] || '';
                            setCardKey(first);
                            setField('cardImage', first ? `asset:${first}` : 'none');
                          } else {
                            setCardKey('');
                            setField('cardImage', 'none');
                          }
                        }}
                      />
                    )}
                    label="Use Card Asset Key"
                  />
                  {useCardAsset ? (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Autocomplete
                        options={cardKeys}
                        disableClearable
                        freeSolo={false}
                        sx={{ flex: 1 }}
                        value={cardKey || null}
                        onChange={(_, v) => {
                          const key = v || '';
                          setCardKey(key);
                          setField('cardImage', key ? `asset:${key}` : 'none');
                        }}
                        renderOption={(props, option) => (
                          <li {...props}>
                            <Stack>
                              <Typography>{option}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {resolveAsset(option, { theme: name, absolute: true })}
                              </Typography>
                            </Stack>
                          </li>
                        )}
                        renderInput={(params) => <TextField {...params} label="Card Image Asset Key" placeholder="cards.*" />}
                      />
                      <IconButton
                        aria-label="open card asset"
                        disabled={!cardKey}
                        onClick={() => {
                          const url = resolveAsset(cardKey, { theme: name, absolute: true });
                          window.open(url, '_blank', 'noopener');
                        }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  ) : (
                    <TextField
                      fullWidth
                      label="Card Image (URL or data URI)"
                      placeholder="e.g., /images/panel-texture.png"
                      value={state.cardImage || 'none'}
                      onChange={(e) => setField('cardImage', e.target.value)}
                    />
                  )}
                  <Button
                    variant="outlined"
                    startIcon={<UploadIcon />}
                    component="label"
                  >
                    Upload Card Image
                    <input
                      hidden
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        setUseCardAsset(false);
                        setCardKey('');
                        uploadToField('cardImage', { cardUseImage: true })(e);
                      }}
                    />
                  </Button>
                </Stack>
                {cardThumb.loading && <Typography variant="caption">Checking…</Typography>}
                {cardThumb.ok === true && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <img src={cardThumb.url} alt="card" style={{ width: 120, height: 60, objectFit: 'cover', borderRadius: 6 }} />
                    <Chip size="small" color="success" label="Loaded" />
                  </Stack>
                )}
                {cardThumb.ok === false && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Chip size="small" color="error" label="Not found / blocked" />
                    <Typography variant="caption">Place file in <code>frontend/static/images</code> / <code>frontend/public/images</code> or choose an Asset Key.</Typography>
                  </Stack>
                )}
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Panel preview
                </Typography>
                <Card
                  sx={{
                    p: 2,
                    background: 'var(--surface)',
                    border: 'var(--border-surface-width,0px) solid var(--border-surface,transparent)'
                  }}
                >
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Surface card
                  </Typography>
                  <Card
                    sx={{
                      p: 1,
                      background: 'var(--card)',
                      border: 'var(--border-card-width,0px) solid var(--border-card,transparent)'
                    }}
                  >
                    <Typography variant="caption">Inner card (var(--card))</Typography>
                  </Card>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <Button variant="contained">Primary</Button>
                    <Button variant="outlined">Outlined</Button>
                    <Chip label="Chip" />
                  </Stack>
                </Card>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Background" />
            <CardContent>
              <Stack spacing={2}>
                <ColorInput label="Page / Wallpaper Base (--page)" value={state.page ?? state.bg} onChange={(v) => setField('page', v)} />
                <FormControlLabel control={<Switch checked={!!state.useImage} onChange={(e) => setField('useImage', e.target.checked)} />} label="Use Image" />
                <Stack spacing={1}>
                  <FormControlLabel
                    control={(
                      <Switch
                        checked={useWallAsset}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setUseWallAsset(checked);
                          if (checked) {
                            const first = wallKeys[0] || '';
                            setWallKey(first);
                            setField('wallpaper', first ? `asset:${first}` : 'none');
                          } else {
                            setWallKey('');
                            setField('wallpaper', 'none');
                          }
                        }}
                      />
                    )}
                    label="Use Asset Key"
                  />
                  {useWallAsset ? (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Autocomplete
                        options={wallKeys}
                        disableClearable
                        freeSolo={false}
                        sx={{ flex: 1 }}
                        value={wallKey || null}
                        onChange={(_, v) => {
                          const key = v || '';
                          setWallKey(key);
                          setField('wallpaper', key ? `asset:${key}` : 'none');
                        }}
                        renderOption={(props, option) => (
                          <li {...props}>
                            <Stack>
                              <Typography>{option}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {resolveAsset(option, { theme: name, absolute: true })}
                              </Typography>
                            </Stack>
                          </li>
                        )}
                        renderInput={(params) => <TextField {...params} label="Wallpaper Asset Key" placeholder="wallpaper.*" />}
                      />
                      <IconButton
                        aria-label="open wallpaper asset"
                        disabled={!wallKey}
                        onClick={() => {
                          const url = resolveAsset(wallKey, { theme: name, absolute: true });
                          window.open(url, '_blank', 'noopener');
                        }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  ) : (
                    <TextField
                      fullWidth
                      label="Wallpaper (URL or data URI)"
                      placeholder="e.g., /images/wally.png"
                      value={state.wallpaper || 'none'}
                      onChange={(e) => setField('wallpaper', e.target.value)}
                    />
                  )}
                  <Button
                    variant="outlined"
                    startIcon={<UploadIcon />}
                    component="label"
                  >
                    Upload Wallpaper
                    <input
                      hidden
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        setUseWallAsset(false);
                        setWallKey('');
                        uploadToField('wallpaper', { useImage: true })(e);
                      }}
                    />
                  </Button>
                </Stack>
                {wallThumb.loading && <Typography variant="caption">Checking…</Typography>}
                {wallThumb.ok === true && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <img src={wallThumb.url} alt="wallpaper" style={{ width: 120, height: 60, objectFit: 'cover', borderRadius: 6 }} />
                    <Chip size="small" color="success" label="Loaded" />
                  </Stack>
                )}
                {wallThumb.ok === false && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Chip size="small" color="error" label="Not found / blocked" />
                    <Typography variant="caption">Use an <b>Asset Key</b> from the dropdown, or place a file in <code>frontend/static/images</code> / <code>frontend/public/images</code> and reference it as <code>/images/&lt;name&gt;</code>.</Typography>
                  </Stack>
                )}
                <Divider />
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 80 }}>Size</Typography>
                  <TextField
                    select
                    size="small"
                    value={state.wallpaperSize || 'cover'}
                    onChange={(e) => setField('wallpaperSize', e.target.value)}
                    sx={{ width: 180 }}
                  >
                    {SIZE_OPTS.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 80 }}>Repeat</Typography>
                  <TextField
                    select
                    size="small"
                    value={state.wallpaperRepeat || 'no-repeat'}
                    onChange={(e) => setField('wallpaperRepeat', e.target.value)}
                    sx={{ width: 180 }}
                  >
                    {REPEAT_OPTS.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 80 }}>Attachment</Typography>
                  <TextField
                    select
                    size="small"
                    value={state.wallpaperAttachment || 'scroll'}
                    onChange={(e) => setField('wallpaperAttachment', e.target.value)}
                    sx={{ width: 180 }}
                  >
                    {ATTACH_OPTS.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Stack spacing={1}>
                  <Typography>Position</Typography>
                  <TextField
                    select
                    size="small"
                    value={posPreset}
                    onChange={(e) => setPosPreset(e.target.value)}
                    sx={{ width: 220 }}
                  >
                    {POS_PRESETS.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </TextField>
                  {posPreset === 'custom' && (
                    <Stack spacing={1}>
                      <Typography variant="caption">Focal point (X/Y %)</Typography>
                      <Stack direction="row" spacing={2} alignItems="center">
                        <Typography variant="caption">X</Typography>
                        <Slider
                          value={xy[0]}
                          min={0}
                          max={100}
                          onChange={(_, value) => {
                            const raw = Array.isArray(value) ? value[0] : value;
                            const clamped = Math.max(0, Math.min(100, Number(raw)));
                            setPosPreset('custom');
                            setXy((prev) => [clamped, prev[1]]);
                          }}
                          sx={{ width: 180 }}
                        />
                        <TextField
                          size="small"
                          type="number"
                          sx={{ width: 80 }}
                          value={xy[0]}
                          onChange={(e) => {
                            const parsed = Number(e.target.value || 0);
                            const clamped = Math.max(0, Math.min(100, parsed));
                            setPosPreset('custom');
                            setXy((prev) => [clamped, prev[1]]);
                          }}
                        />
                      </Stack>
                      <Stack direction="row" spacing={2} alignItems="center">
                        <Typography variant="caption">Y</Typography>
                        <Slider
                          value={xy[1]}
                          min={0}
                          max={100}
                          onChange={(_, value) => {
                            const raw = Array.isArray(value) ? value[0] : value;
                            const clamped = Math.max(0, Math.min(100, Number(raw)));
                            setPosPreset('custom');
                            setXy((prev) => [prev[0], clamped]);
                          }}
                          sx={{ width: 180 }}
                        />
                        <TextField
                          size="small"
                          type="number"
                          sx={{ width: 80 }}
                          value={xy[1]}
                          onChange={(e) => {
                            const parsed = Number(e.target.value || 0);
                            const clamped = Math.max(0, Math.min(100, parsed));
                            setPosPreset('custom');
                            setXy((prev) => [prev[0], clamped]);
                          }}
                        />
                      </Stack>
                    </Stack>
                  )}
                </Stack>
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Overlay
                </Typography>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 80 }}>Color</Typography>
                  <input
                    type="color"
                    value={overlayColor}
                    onChange={(e) => {
                      setSimpleOverlayActive(true);
                      setOverlayColor(e.target.value);
                    }}
                    style={{ width: 48, height: 32, border: 'none', background: 'transparent' }}
                  />
                  <Typography sx={{ minWidth: 80, ml: 2 }}>Opacity</Typography>
                  <Slider
                    value={overlayAlpha}
                    min={0}
                    max={0.85}
                    step={0.05}
                    onChange={(_, value) => {
                      const raw = Array.isArray(value) ? value[0] : value;
                      const clamped = Math.max(0, Math.min(1, Number(raw)));
                      setSimpleOverlayActive(true);
                      setOverlayAlpha(clamped);
                    }}
                    sx={{ width: 180 }}
                  />
                  <TextField
                    size="small"
                    sx={{ width: 80 }}
                    value={overlayAlpha}
                    onChange={(e) => {
                      const parsed = Number(e.target.value || 0);
                      const clamped = Math.max(0, Math.min(1, parsed));
                      setSimpleOverlayActive(true);
                      setOverlayAlpha(clamped);
                    }}
                  />
                </Stack>
                <TextField
                  fullWidth
                  label="Advanced overlay CSS (optional)"
                  placeholder="e.g., linear-gradient(rgba(0,0,0,.35), rgba(0,0,0,.35))"
                  value={state.wallpaperOverlay || 'none'}
                  onChange={(e) => {
                    setSimpleOverlayActive(false);
                    setOverlayAlpha(0);
                    setField('wallpaperOverlay', e.target.value);
                  }}
                  helperText="If set, overrides the simple color/opacity above."
                />
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Canvas preview
                </Typography>
                <Box
                  sx={{
                    borderRadius: 2,
                    minHeight: 100,
                    backgroundColor: 'var(--page)',
                    backgroundImage: 'var(--wall-overlay, none), var(--body-bg-image)',
                    backgroundSize: 'auto, var(--wall-size, cover)',
                    backgroundPosition: 'center, var(--wall-position, center)',
                    backgroundRepeat: 'no-repeat, var(--wall-repeat, no-repeat)',
                    backgroundAttachment: 'scroll, var(--wall-attach, fixed)',
                    border: '1px solid rgba(255,255,255,0.08)'
                  }}
                />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

