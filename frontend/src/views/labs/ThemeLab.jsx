import React, { useMemo, useState, useEffect } from 'react';
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

  useEffect(() => {
    if (!livePreview) return;
    previewTokens(name, state);
    return () => {};
  }, [name, state, livePreview]);

  useEffect(() => () => clearPreview(), []);

  useEffect(() => {
    const v = state.wallpaper;
    if (!state.useImage || !v || v === 'none') {
      setWallThumb({ url: '', ok: null, loading: false });
      return;
    }
    const url = v.startsWith('data:') ? v : v.startsWith('http') ? v : `${location.origin}${v.startsWith('/') ? '' : '/'}${v}`;
    setWallThumb({ url, ok: null, loading: true });
    const img = new Image();
    img.onload = () => setWallThumb({ url, ok: true, loading: false });
    img.onerror = () => setWallThumb({ url, ok: false, loading: false });
    img.src = url;
  }, [state.wallpaper, state.useImage]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Theme Lab</Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>Edit colors & wallpaper per theme. Changes save to your browser and apply instantly.</Typography>
      <Card>
        <CardHeader
          title="Editor"
          subheader={(
            <Stack direction="row" spacing={2}>
              <Tooltip title="The UI mode currently applied by the header toggle">
                <Chip size="small" label={`Active UI Mode: ${document.documentElement.dataset.theme || 'unknown'}`} />
              </Tooltip>
              <Tooltip title="The theme you are editing in this panel">
                <Chip size="small" color="primary" variant="outlined" label={`Editing: ${name}`} />
              </Tooltip>
              {document.documentElement.dataset.theme !== name && (
                <Tooltip title="You are editing a different theme than the one currently active — toggle the header to this theme or use Live Preview">
                  <Chip size="small" color="warning" label="Note: editing ≠ active" />
                </Tooltip>
              )}
            </Stack>
          )}
        />
        <CardContent>
          <Stack spacing={3}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography sx={{ minWidth: 120 }}>Theme</Typography>
              <TextField select size="small" value={name} onChange={(e) => { const n = e.target.value; setName(n); setState(loadTokens(n)); }}>
                {THEME_NAMES.map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
              </TextField>
              <FormControlLabel control={<Switch checked={livePreview} onChange={(e) => setLivePreview(e.target.checked)} />} label="Live Preview" />
              <Button variant="outlined" onClick={resetToDefaults}>Revert to Defaults</Button>
              <Button variant="contained" onClick={save}>Save & Apply</Button>
              <Button color="error" onClick={remove}>Remove Override</Button>
              <Button onClick={discard}>Discard Unsaved</Button>
              <Button onClick={() => { resetAllThemeData(); setState(loadTokens(name)); }} title="Clears all saved theme data for all themes">Reset All</Button>
            </Stack>
            <Divider />
            <Stack direction="row" spacing={2} alignItems="center">
              <Button variant="contained">Primary Button</Button>
              <Button variant="outlined">Outlined</Button>
              <Chip label="Chip" />
              <Card sx={{ p: 1, minWidth: 160 }}><Typography variant="body2">Card sample</Typography></Card>
            </Stack>
            <Divider />
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Stack spacing={2}>
                  <ColorInput label="Page / Wallpaper Base (--page)" value={state.page ?? state.bg} onChange={(v) => setField('page', v)} />
                  <ColorInput label="Background (--bg)" value={state.bg} onChange={(v) => setField('bg', v)} />
                  <ColorInput label="Surface / Paper (--surface)" value={state.surface} onChange={(v) => setField('surface', v)} />
                  <ColorInput label="Card (--card)" value={state.card} onChange={(v) => setField('card', v)} />
                  <ColorInput label="Text (--text)" value={state.text} onChange={(v) => setField('text', v)} />
                  <ColorInput label="Primary (--primary)" value={state.primary} onChange={(v) => setField('primary', v)} />
                </Stack>
              </Grid>
              <Grid item xs={12} md={6}>
                <Stack spacing={2}>
                  <FormControlLabel control={<Switch checked={!!state.useImage} onChange={(e) => setField('useImage', e.target.checked)} />} label="Use Image" />
                  <Typography>Wallpaper (URL or data URI)</Typography>
                  <TextField
                    fullWidth
                    placeholder="e.g., /images/wally.png or data:image/png;base64,..."
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
                      <Typography variant="caption">Ensure the path is reachable. For local files in the app, use a leading slash like <code>/images/wally.png</code>.</Typography>
                    </Stack>
                  )}
                  <Typography variant="caption">Tip: toggle <b>Use Image</b> off to show only the Page color.</Typography>
                </Stack>
              </Grid>
            </Grid>
            <Divider />
            <Card sx={{ mt: 2, p: 2, minHeight: 120, background: 'var(--surface)' }}>
              <Box
                sx={{
                  borderRadius: 2,
                  minHeight: 120,
                  backgroundColor: 'var(--page)',
                  backgroundImage: 'var(--body-bg-image)',
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  border: '1px solid rgba(255,255,255,0.08)'
                }}
              />
            </Card>
            <Divider />
            <Stack direction="row" spacing={2}>
              <Button variant="outlined" onClick={doExport}>Export JSON</Button>
              <Button component="label" variant="outlined">
                Import JSON
                <input hidden type="file" accept="application/json" onChange={doImport} />
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

