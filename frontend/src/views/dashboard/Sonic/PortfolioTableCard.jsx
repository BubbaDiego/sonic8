import React, { useState } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Typography
} from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';

const initialPositions = [
  { id: 1, asset: 'BTC', quantity: 1.2, price: 32000, collateral: 15000 },
  { id: 2, asset: 'ETH', quantity: 10, price: 2000, collateral: 12000 },
  { id: 3, asset: 'SOL', quantity: 500, price: 40, collateral: 5000 },
];

const PortfolioTableCard = () => {
  const [positions, setPositions] = useState(initialPositions);
  const [orderBy, setOrderBy] = useState('asset');
  const [order, setOrder] = useState('asc');

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);

    setPositions((prevPositions) =>
      [...prevPositions].sort((a, b) => {
        if (isAsc) return b[property] < a[property] ? -1 : 1;
        return a[property] < b[property] ? -1 : 1;
      })
    );
  };

  return (
    <MainCard>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Portfolio Positions
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              {['asset', 'quantity', 'price', 'collateral'].map((col) => (
                <TableCell key={col}>
                  <TableSortLabel active={orderBy === col} direction={orderBy === col ? order : 'asc'} onClick={() => handleSort(col)}>
                    {col.charAt(0).toUpperCase() + col.slice(1)}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((position) => (
              <TableRow key={position.id}>
                <TableCell>{position.asset}</TableCell>
                <TableCell>{position.quantity}</TableCell>
                <TableCell>${position.price.toLocaleString()}</TableCell>
                <TableCell>${position.collateral.toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </MainCard>
  );
};

export default PortfolioTableCard;
