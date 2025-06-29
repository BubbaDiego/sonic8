import React, { useState, useEffect } from 'react';
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
import axios from 'utils/axios';

const PortfolioTableCard = () => {
  const [positions, setPositions] = useState([]);
  const [totals, setTotals] = useState({ value: 0, collateral: 0 });
  const [orderBy, setOrderBy] = useState('asset_type');
  const [order, setOrder] = useState('asc');

  useEffect(() => {
    async function loadPositions() {
      try {
        const response = await axios.get('/positions');
        const data = response.data || [];
        setPositions(data);
        const totalValue = data.reduce((sum, p) => sum + parseFloat(p.value || 0), 0);
        const totalCollateral = data.reduce(
          (sum, p) => sum + parseFloat(p.collateral || 0),
          0
        );
        setTotals({ value: totalValue, collateral: totalCollateral });
      } catch (e) {
        // API failure is non-fatal for UI
        console.error(e);
      }
    }
    loadPositions();
  }, []);

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
              {['asset_type', 'size', 'value', 'collateral'].map((col) => (
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
                <TableCell>{position.asset_type}</TableCell>
                <TableCell>{position.size}</TableCell>
                <TableCell>${Number(position.value || 0).toLocaleString()}</TableCell>
                <TableCell>${Number(position.collateral || 0).toLocaleString()}</TableCell>
              </TableRow>
            ))}
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Totals</TableCell>
              <TableCell></TableCell>
              <TableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.value).toLocaleString()}
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.collateral).toLocaleString()}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </MainCard>
  );
};

export default PortfolioTableCard;
