import { useState, useMemo } from 'react';
import useSWR from 'swr';
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
  CircularProgress
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import MainCard from 'ui-component/cards/MainCard';
import { fetcher } from 'utils/axios';

const TABLES = [
  { label: 'Positions', value: 'positions' },
  { label: 'Portfolio', value: 'portfolio' },
  { label: 'Wallets', value: 'wallets' },
  { label: 'Traders', value: 'api/traders' },
  { label: 'Alerts', value: 'alert_thresholds' }
];

export default function DatabaseViewer() {
  const [table, setTable] = useState(TABLES[0].value);
  const { data, error, isLoading } = useSWR(`/${table}/`, fetcher);

  const columns = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return Object.keys(data[0]).map((key) => ({
      field: key,
      headerName: key,
      flex: 1,
      minWidth: 120
    }));
  }, [data]);

  let content;
  if (isLoading) {
    content = (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
      </Box>
    );
  } else if (error) {
    const msg = typeof error === 'string' ? error : error?.message || 'Error';
    content = (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error">{msg}</Typography>
      </Box>
    );
  } else {
    const rows = (Array.isArray(data) ? data : []).map((row, idx) => ({
      id: row.id ?? idx,
      ...row
    }));
    content = (
      <Box sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={rows}
          columns={columns}
          pageSizeOptions={[25]}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
          disableRowSelectionOnClick
        />
      </Box>
    );
  }

  return (
    <MainCard title="Database Viewer">
      <FormControl size="small" sx={{ mb: 2, minWidth: 160 }}>
        <InputLabel id="db-table-label">Table</InputLabel>
        <Select
          labelId="db-table-label"
          label="Table"
          value={table}
          onChange={(e) => setTable(e.target.value)}
        >
          {TABLES.map((t) => (
            <MenuItem key={t.value} value={t.value}>
              {t.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {content}
    </MainCard>
  );
}
