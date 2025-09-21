import React, { useMemo, useState, useEffect, useRef } from 'react';
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

const THEME_NAMES = ['light', 'dark', 'funky'];
const FONT_OPTIONS = ['System UI', 'Roboto', 'Inter', 'Poppins', 'Space Grotesk', 'Orbitron', 'Neuropol', 'JetBrains Mono'];
const ColorInput = ({ label, value, onChange }) => (
  <Stack direction="row" alignItems="center" spacing={2}>
    <Typography sx={{ minWidth: 120 }}>{label}</Typography>
    <input type="color" value={value} onChange={(e) => onChange(e.target.value)} style={{ width: 48, height: 32, border: 'none', background: 'transparent' }} />
    <TextField size="small" value={value} onChange={(e) => onChange(e.target.value)} sx={{ width: 160 }} />
  </Stack>
);

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
      const next = { ...s, [k]: v };
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
    const url = isAssetPointer(v)
      ? resolveAsset(toAssetKey(v), { theme: name, absolute: true })
      : normalize(v);
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
    const url = isAssetPointer(v)
      ? resolveAsset(toAssetKey(v), { theme: name, absolute: true })
      : normalize(v);
    setCardThumb({ url, ok: null, loading: true });
    const img = new Image();
    img.onload = () => setCardThumb({ url, ok: true, loading: false });
    img.onerror = () => setCardThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.cardImage, state.cardUseImage, useCardAsset, cardKey, name]);

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
        <Grid item xs={12} md={4}>
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
                      onChange={(_, value) => setField('fontSize', Array.isArray(value) ? value[0] : value)}
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
                <ColorInput label="Text (--text)" value={state.text} onChange={(v) => setField('text', v)} />
                <Divider />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Live text preview
                </Typography>
                <Typography variant="h6">Heading 6</Typography>
                <Typography variant="body2">The quick brown fox jumps over the lazy dog — 1234567890.</Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
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
                    <Autocomplete
                      options={wallKeys}
                      value={wallKey || null}
                      onChange={(_, v) => {
                        const key = v || '';
                        setWallKey(key);
                        setField('wallpaper', key ? `asset:${key}` : 'none');
                      }}
                      renderInput={(params) => <TextField {...params} label="Wallpaper Asset Key" placeholder="wallpaper.*" />}
                    />
                  ) : (
                    <TextField
                      fullWidth
                      label="Wallpaper (URL or data URI)"
                      placeholder="e.g., /images/wally.png"
                      value={state.wallpaper || 'none'}
                      onChange={(e) => setField('wallpaper', e.target.value)}
                    />
                  )}
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
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Canvas preview
                </Typography>
                <Box
                  sx={{
                    borderRadius: 2,
                    minHeight: 100,
                    backgroundColor: 'var(--page)',
                    backgroundImage: 'var(--body-bg-image)',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    border: '1px solid rgba(255,255,255,0.08)'
                  }}
                />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
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
                    <Autocomplete
                      options={cardKeys}
                      value={cardKey || null}
                      onChange={(_, v) => {
                        const key = v || '';
                        setCardKey(key);
                        setField('cardImage', key ? `asset:${key}` : 'none');
                      }}
                      renderInput={(params) => <TextField {...params} label="Card Image Asset Key" placeholder="cards.*" />}
                    />
                  ) : (
                    <TextField
                      fullWidth
                      label="Card Image (URL or data URI)"
                      placeholder="e.g., /images/panel-texture.png"
                      value={state.cardImage || 'none'}
                      onChange={(e) => setField('cardImage', e.target.value)}
                    />
                  )}
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
                <Card sx={{ p: 2, background: 'var(--surface)' }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Surface card
                  </Typography>
                  <Card sx={{ p: 1, background: 'var(--card)' }}>
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
      </Grid>
    </Box>
  );
}

