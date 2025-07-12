import React from 'react';
import { Box, Typography, Chip, Stack } from '@mui/material';
import TraderEnhancedTable from './TraderEnhancedTable';
import { useTraders } from './hooks';

const safeNumber = (n, digits = 2) => (n != null ? n.toFixed(digits) : '—');

export default function TraderShopList() {
  const { traders, isLoading, isError } = useTraders();

  const cols = [
    { id: 'avatar', label: 'Avatar', format: (row) => <img src={row.avatar} width={30} alt={row.name} /> },
    { id: 'name', label: 'Name' },
    { id: 'wallet_balance', label: 'Balance', format: (row) => safeNumber(row.wallet_balance) },
    { id: 'profit', label: 'Profit', format: (row) => (
      <Typography color={row.profit >= 0 ? 'success.main' : 'error.main'}>
        {safeNumber(row.profit)}
      </Typography>
    ) },
    { id: 'heat_index', label: 'Heat Index', format: (row) => (
      <Chip label={safeNumber(row.heat_index, 1)} size="small" />
    ) },
  ];

  if (isLoading) return <div>Loading traders...</div>;
  if (isError) return <div>Error loading traders!</div>;

  return (
    <Box sx={{ padding: 2 }}>
      <Stack spacing={2}>
        <Typography variant="h4">Trader Shop</Typography>
        <TraderEnhancedTable
          headCells={cols}
          rows={traders}
        />
      </Stack>
    </Box>
  );
}
