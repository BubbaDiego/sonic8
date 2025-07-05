import { useState, useCallback } from 'react';
import useSWR from 'swr';
import { Box, Button, Stack, Tab, Tabs, Switch, FormControlLabel } from '@mui/material';
import axios, { fetcher } from 'utils/axios';
import { useDispatch } from 'store';
import { openSnackbar } from 'store/slices/snackbar';
import ThresholdsTable from './ThresholdsTable';

export default function ThresholdsPage() {
  const dispatch = useDispatch();
  const [tab, setTab] = useState(0);
  const [monitorEnabled, setMonitorEnabled] = useState(true);
  const { data: thresholds = [], mutate } = useSWR('/alert_thresholds/', fetcher);

  const updateRow = useCallback(
    async (row) => {
      await axios.put(`/alert_thresholds/${row.id}`, row);
      mutate();
    },
    [mutate]
  );

  const handleSave = async () => {
    try {
      await axios.put('/alert_thresholds/bulk', { thresholds, monitorEnabled });
      dispatch(
        openSnackbar({
          open: true,
          message: 'Configuration saved',
          variant: 'alert',
          alert: { color: 'success' },
          close: false
        })
      );
    } catch (err) {
      dispatch(
        openSnackbar({
          open: true,
          message: 'Save failed',
          variant: 'alert',
          alert: { color: 'error' },
          severity: 'error',
          close: false
        })
      );
    }
  };

  const handleExport = async () => {
    try {
      const res = await axios.get('/alert_thresholds/bulk');
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
      );
      const a = document.createElement('a');
      a.href = url;
      a.download = 'alert_thresholds.json';
      a.click();
      URL.revokeObjectURL(url);
      dispatch(
        openSnackbar({
          open: true,
          message: 'Exported',
          variant: 'alert',
          alert: { color: 'success' },
          close: false
        })
      );
    } catch (err) {
      dispatch(
        openSnackbar({
          open: true,
          message: 'Export failed',
          variant: 'alert',
          alert: { color: 'error' },
          severity: 'error',
          close: false
        })
      );
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      await axios.put('/alert_thresholds/bulk', JSON.parse(text));
      mutate();
      dispatch(
        openSnackbar({
          open: true,
          message: 'Configuration imported',
          variant: 'alert',
          alert: { color: 'success' },
          close: false
        })
      );
    } catch (err) {
      dispatch(
        openSnackbar({
          open: true,
          message: 'Import failed',
          variant: 'alert',
          alert: { color: 'error' },
          severity: 'error',
          close: false
        })
      );
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button variant="contained" onClick={handleSave} data-testid="save-btn">
          Save
        </Button>
        <Button component="label" variant="outlined">
          Import
          <input hidden type="file" accept="application/json" onChange={handleImport} />
        </Button>
        <Button variant="outlined" onClick={handleExport} data-testid="export-btn">
          Export
        </Button>
      </Stack>
      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Thresholds" />
        <Tab label="Settings" />
      </Tabs>
      {tab === 0 && <ThresholdsTable rows={thresholds} updateRow={updateRow} />}
      {tab === 1 && (
        <Box sx={{ p: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={monitorEnabled}
                onChange={(e) => setMonitorEnabled(e.target.checked)}
              />
            }
            label="Enable Monitors"
          />
        </Box>
      )}
    </Box>
  );
}
