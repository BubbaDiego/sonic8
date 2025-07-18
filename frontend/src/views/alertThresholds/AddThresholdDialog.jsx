import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem } from '@mui/material';
import { useState } from 'react';
import { useDispatch } from 'store';
import { createThreshold } from 'store/slices/alertThresholds';
import { openSnackbar } from 'store/slices/snackbar';

const PRESETS = [
  {
    key: 'liquidationdistance',
    label: 'Liquidation Distance',
    row: {
      alert_type: 'LiquidationDistance',
      alert_class: 'Position',
      metric_key: 'liquidation_distance',
      condition: 'BELOW',
      low: 0,
      medium: 0,
      high: 0,
      enabled: true
    }
  },
  {
    key: 'profit',
    label: 'Profit',
    row: {
      alert_type: 'Profit',
      alert_class: 'Position',
      metric_key: 'pnl_after_fees_usd',
      condition: 'ABOVE',
      low: 0,
      medium: 0,
      high: 0,
      enabled: true
    }
  }
];

export default function AddThresholdDialog({ open, onClose, onCreated }) {
  const dispatch = useDispatch();
  const [preset, setPreset] = useState(PRESETS[0].key);

  const handleAdd = async () => {
    const p = PRESETS.find((x) => x.key === preset);
    if (!p) return onClose();
    const res = await dispatch(createThreshold(p.row));
    if (!res.error) {
      onCreated?.(res.payload);
      dispatch(
        openSnackbar({
          open: true,
          message: 'Threshold created',
          variant: 'alert',
          alert: { color: 'success' },
          close: false
        })
      );
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>➕ Add Threshold</DialogTitle>
      <DialogContent dividers>
        <TextField
          select
          fullWidth
          margin="dense"
          label="Preset"
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
        >
          {PRESETS.map((p) => (
            <MenuItem key={p.key} value={p.key}>
              {p.label}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleAdd}>
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}
