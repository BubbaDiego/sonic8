import React, { useEffect, useMemo, useState } from 'react';
import { Box, TextField, MenuItem, Tooltip, IconButton } from '@mui/material';
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';
import { getProfiles, ensureProfilesInitialized } from 'theme/tokens';
import PaletteIcon from '@mui/icons-material/Palette';

export default function ThemeModeSection() {
  const { mode, onChangeMode, setMode } = useConfig();
  const [profiles, setProfiles] = useState([]);
  useEffect(() => {
    ensureProfilesInitialized();
    setProfiles(getProfiles());
  }, []);
  const options = useMemo(() => ['system', ...profiles], [profiles]);
  const value = String(mode || 'dark');
  const handleChange = (e) => {
    const v = e.target.value;
    if (v === 'system') {
      if (onChangeMode) onChangeMode(ThemeMode.SYSTEM);
      else if (setMode) setMode(ThemeMode.SYSTEM);
    } else {
      if (onChangeMode) onChangeMode(v);
      else if (setMode) setMode(v);
    }
  };
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <TextField select size="small" value={value} onChange={handleChange} sx={{ minWidth: 160 }}>
        {options.map((opt) => (
          <MenuItem key={opt} value={opt}>
            {opt}
          </MenuItem>
        ))}
      </TextField>
      <Tooltip title="Manage themes">
        <IconButton size="small" onClick={() => (window.location.href = '/sonic-labs/theme-lab')}>
          <PaletteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );
}
