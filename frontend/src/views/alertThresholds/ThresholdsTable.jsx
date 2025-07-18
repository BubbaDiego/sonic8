import { useCallback } from 'react';
import { Box } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { useDispatch } from 'store';
import { openSnackbar } from 'store/slices/snackbar';
import MainCard from 'ui-component/cards/MainCard';
import { typeIcons } from './icons';

export default function ThresholdsTable({ rows = [], updateRow }) {
  const dispatch = useDispatch();

  const processRowUpdate = useCallback(
    async (newRow) => {
      await updateRow(newRow);
      dispatch(
        openSnackbar({
          open: true,
          message: 'Threshold saved',
          variant: 'alert',
          alert: { color: 'success' },
          close: false
        })
      );
      return newRow;
    },
    [updateRow, dispatch]
  );

  const handleError = useCallback(
    (error) => {
      dispatch(
        openSnackbar({
          open: true,
          message: error?.message || 'Update failed',
          variant: 'alert',
          alert: { color: 'error' },
          severity: 'error',
          close: false
        })
      );
    },
    [dispatch]
  );

  const columns = [
    {
      field: 'alert_type',
      headerName: 'Type',
      flex: 1,
      minWidth: 160,
      editable: true,
      renderCell: ({ value }) => {
        const Icon = typeIcons[value];
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {Icon && <Icon size={16} />}
            {value}
          </Box>
        );
      }
    },
    { field: 'alert_class', headerName: 'Class', flex: 1, minWidth: 130, editable: true },
    { field: 'metric_key', headerName: 'Metric', flex: 1, minWidth: 140, editable: true },
    { field: 'condition', headerName: 'Cond', flex: 0.6, minWidth: 100, editable: true },
    { field: 'low', headerName: 'Low', type: 'number', flex: 0.6, minWidth: 100, editable: true },
    { field: 'medium', headerName: 'Medium', type: 'number', flex: 0.6, minWidth: 100, editable: true },
    { field: 'high', headerName: 'High', type: 'number', flex: 0.6, minWidth: 100, editable: true },
    { field: 'enabled', headerName: 'Enabled', type: 'boolean', flex: 0.6, minWidth: 100, editable: true }
  ];

  return (
    <MainCard content={false} title="Alert Thresholds">
      <Box sx={{ width: '100%' }}>
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(row) => row.id}
          hideFooter
          processRowUpdate={processRowUpdate}
          onProcessRowUpdateError={handleError}
          className="custom-data-grid"
        />
      </Box>
    </MainCard>
  );
}
