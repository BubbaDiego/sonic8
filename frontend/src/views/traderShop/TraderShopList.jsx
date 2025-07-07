// src/views/traderShop/TraderShopList.jsx
import React, { useState } from 'react';
import { Box, Button, Stack, Typography, Chip } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DownloadIcon from '@mui/icons-material/Download';
import EnhancedTable from 'views/forms/tables/TableEnhanced';
import TraderFormDrawer from './TraderFormDrawer';
import QuickImportStarWars from './QuickImportStarWars';
import { useTraders, deleteTrader, exportTraders } from './hooks';

function TraderShopList() {
  const { traders, isLoading } = useTraders();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const openNew = () => {
    setEditing(null);
    setDrawerOpen(true);
  };

  const handleRowClick = (row) => {
    setEditing(row);
    setDrawerOpen(true);
  };

  const handleDelete = async (row) => {
    if (window.confirm(`Delete trader ${row.name}?`)) {
      await deleteTrader(row.name);
    }
  };

  const cols = [
    {
      id: 'avatar',
      label: '',
      align: 'center',
      format: (row) => (row.avatar ? row.avatar : '🧙')
    },
    { id: 'name', label: 'Name', format: (row) => row.name },
    { id: 'persona', label: 'Persona' },
    { id: 'wallet_balance', label: 'Balance', align: 'right' },
    {
      id: 'profit',
      label: 'P&L',
      align: 'right',
      format: (row) => (
        <Typography color={row.profit >= 0 ? 'success.main' : 'error.main'}>
          {row.profit.toFixed(2)}
        </Typography>
      )
    },
    {
      id: 'heat_index',
      label: 'Heat',
      align: 'center',
      format: (row) => <Chip label={row.heat_index.toFixed(1)} size="small" />
    }
  ];

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" mb={2} alignItems="center">
        <Typography variant="h4">Trader Shop</Typography>
        <Stack direction="row">
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openNew}
            sx={{ mr: 1 }}
          >
            New Trader
          </Button>
          <QuickImportStarWars />
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={exportTraders}
            sx={{ ml: 1 }}
          >
            Export
          </Button>
        </Stack>
      </Stack>

      <EnhancedTable
        headCells={cols}
        rows={traders}
        loading={isLoading}
        onRowClick={handleRowClick}
        onDelete={handleDelete}
        dense
        toolbar={false}
      />

      <TraderFormDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        initial={editing}
      />
    </Box>
  );
}

export default TraderShopList;
