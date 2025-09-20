import React, { useMemo, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import { DEFAULT_TOKENS, loadTokens, saveTokens, removeTokens, exportAllThemes, importAllThemes } from '../../theme/tokens';

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
  const base = useMemo(() => DEFAULT_TOKENS[name], [name]);

  const setField = (k, v) => setState((s) => ({ ...s, [k]: v }));
  const resetToDefaults = () => setState(base);
  const save = () => {
    saveTokens(name, state);
  };
  const remove = () => {
    removeTokens(name);
    setState(loadTokens(name));
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
      setState(loadTokens(name));
    } catch {
      alert('Invalid JSON');
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Theme Lab</Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>Edit colors & wallpaper per theme. Changes save to your browser and apply instantly.</Typography>
      <Card>
        <CardHeader title="Editor" />
        <CardContent>
          <Stack spacing={3}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography sx={{ minWidth: 120 }}>Theme</Typography>
              <TextField select size="small" value={name} onChange={(e) => { const n = e.target.value; setName(n); setState(loadTokens(n)); }}>
                {THEME_NAMES.map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
              </TextField>
              <Button variant="outlined" onClick={resetToDefaults}>Reset to defaults</Button>
              <Button variant="contained" onClick={save}>Save & Apply</Button>
              <Button color="error" onClick={remove}>Remove Override</Button>
            </Stack>
            <Divider />
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Stack spacing={2}>
                  <ColorInput label="Background (--bg)" value={state.bg} onChange={(v) => setField('bg', v)} />
                  <ColorInput label="Surface / Paper (--surface)" value={state.surface} onChange={(v) => setField('surface', v)} />
                  <ColorInput label="Card (--card)" value={state.card} onChange={(v) => setField('card', v)} />
                  <ColorInput label="Text (--text)" value={state.text} onChange={(v) => setField('text', v)} />
                  <ColorInput label="Primary (--primary)" value={state.primary} onChange={(v) => setField('primary', v)} />
                </Stack>
              </Grid>
              <Grid item xs={12} md={6}>
                <Stack spacing={2}>
                  <Typography>Wallpaper (URL or data URI)</Typography>
                  <TextField
                    fullWidth
                    placeholder="e.g., /images/abstract_mural.png or data:image/png;base64,..."
                    value={state.wallpaper || 'none'}
                    onChange={(e) => setField('wallpaper', e.target.value)}
                  />
                  <Typography variant="caption">Tip: leave <code>none</code> for no wallpaper.</Typography>
                </Stack>
              </Grid>
            </Grid>
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

