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
  const [name, setName] = useState('dark');
  const [state, setState] = useState(loadTokens('dark'));
  const [livePreview, setLivePreview] = useState(true);
  const [wallThumb, setWallThumb] = useState({ url: '', ok: null, loading: false });
  const [cardThumb, setCardThumb] = useState({ url: '', ok: null, loading: false });

  const base = useMemo(() => DEFAULT_TOKENS[name], [name]);

  const setField = (k, v) => setState((s) => ({ ...s, [k]: v }));
  const resetToDefaults = () => setState(base);
  const save = () => {
    saveTokens(name, state);
    clearPreview();
  };
  const remove = () => {
    removeTokens(name);
    const fresh = loadTokens(name);
    setState(fresh);
    if (livePreview) previewTokens(name, fresh);
  };
  const discard = () => {
    const fresh = loadTokens(name);
    setState(fresh);
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
      setState(fresh);
      if (livePreview) previewTokens(name, fresh);
    } catch {
      alert('Invalid JSON');
    }
  };

  const previewTimer = useRef(null);
  useEffect(() => {
    if (!livePreview) return;
    if (previewTimer.current) clearTimeout(previewTimer.current);
    const snapshotName = name;
    const snapshotState = state;
    previewTimer.current = setTimeout(() => {
      previewTokens(snapshotName, snapshotState);
    }, 100);
    return () => {
      if (previewTimer.current) clearTimeout(previewTimer.current);
    };
  }, [name, state, livePreview]);

  useEffect(() => () => clearPreview(), []);

  useEffect(() => {
    const v = state.wallpaper;
    if (!state.useImage || !v || v === 'none') {
      setWallThumb({ url: '', ok: null, loading: false });
      return;
    }
    // Normalize with BASE_URL so /images/* works regardless of deploy base
    const base = import.meta.env?.BASE_URL ? String(import.meta.env.BASE_URL) : '/';
    const join = (a, b) => a.replace(/\/+$/, '/') + b.replace(/^\/+/, '');
    const url = v.startsWith('data:') ? v : /^https?:\/\//i.test(v) ? v : join(location.origin + base, v);
    setWallThumb((prev) => {
      if (prev.url === url && prev.loading === true) {
        return prev;
      }
      return { url, ok: null, loading: true };
    });
    const img = new Image();
    img.onload = () => setWallThumb({ url, ok: true, loading: false });
    img.onerror = () => setWallThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.wallpaper, state.useImage]);

  // Card image thumbnail + validation
  useEffect(() => {
    const v = state.cardImage;
    if (!state.cardUseImage || !v || v === 'none') {
      setCardThumb({ url: '', ok: null, loading: false });
      return;
    }
    const base = import.meta.env?.BASE_URL ? String(import.meta.env.BASE_URL) : '/';
    const join = (a, b) => a.replace(/\/+$/, '/') + b.replace(/^\/+/, '');
    const url = v.startsWith('data:') ? v : /^https?:\/\//i.test(v) ? v : join(location.origin + base, v);
    setCardThumb({ url, ok: null, loading: true });
    const img = new Image();
    img.onload = () => setCardThumb({ url, ok: true, loading: false });
    img.onerror = () => setCardThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.cardImage, state.cardUseImage]);

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
                  setName(n);
                  setState(loadTokens(n));
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
                  setState(loadTokens(name));
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
                <TextField
                  fullWidth
                  label="Wallpaper (URL or data URI)"
                  placeholder="e.g., /images/wally.png"
                  value={state.wallpaper || 'none'}
                  onChange={(e) => setField('wallpaper', e.target.value)}
                />
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
                    <Typography variant="caption">
                      Place it in <code>frontend/static/images</code> (or <code>frontend/public/images</code>) and use <code>/images/&lt;name&gt;</code>.
                    </Typography>
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
                <TextField
                  fullWidth
                  label="Card Image (URL or data URI)"
                  placeholder="e.g., /images/panel-texture.png"
                  value={state.cardImage || 'none'}
                  onChange={(e) => setField('cardImage', e.target.value)}
                />
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
                    <Typography variant="caption">
                      Place file in <code>frontend/static/images</code> (or <code>frontend/public/images</code>) and use <code>/images/&lt;name&gt;</code>.
                    </Typography>
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

