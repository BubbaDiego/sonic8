import React, { useState, useEffect } from 'react';
import {
  Avatar,
  Table,
  TableBody,
  TableContainer,
  TableHead,
  TableSortLabel,
  Paper,
  Typography,
  TableCell,
  TableRow
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { tableCellClasses } from '@mui/material/TableCell';
import MainCard from 'ui-component/cards/MainCard';
import axios from 'utils/axios';

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.common.black,
    color: theme.palette.common.white
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14
  }
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover
  },
  '&:last-of-type td, &:last-of-type th': {
    border: 0
  }
}));

const PortfolioTableCard = () => {
  const [positions, setPositions] = useState([]);
  const [totals, setTotals] = useState({ value: 0, collateral: 0 });
  const [orderBy, setOrderBy] = useState('asset_type');
  const [order, setOrder] = useState('asc');

  useEffect(() => {
    async function loadPositions() {
      try {
        const response = await axios.get('/positions/');
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
        <Table sx={{ minWidth: 320 }} aria-label="portfolio positions table">
          <TableHead>
            <TableRow>
              {['wallet_name', 'asset_type', 'size', 'value', 'collateral'].map((col) => (
                <StyledTableCell key={col}>
                  <TableSortLabel active={orderBy === col} direction={orderBy === col ? order : 'asc'} onClick={() => handleSort(col)}>
                    {col === 'wallet_name' ? 'Wallet' : col.charAt(0).toUpperCase() + col.slice(1)}
                  </TableSortLabel>
                </StyledTableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((position) => (
              <StyledTableRow hover key={position.id}>
                <StyledTableCell>
                  <Avatar
                    src={`/static/images/${(position.wallet_name || 'unknown')
                      .replace(/\s+/g, '')
                      .replace(/vault$/i, '')
                      .toLowerCase()}_icon.jpg`}
                    alt={position.wallet_name}
                    sx={{ width: 24, height: 24 }}
                  />
                </StyledTableCell>
                <StyledTableCell>{position.asset_type}</StyledTableCell>
                <StyledTableCell>{position.size}</StyledTableCell>
                <StyledTableCell>
                  ${Number(position.value || 0).toLocaleString()}
                </StyledTableCell>
                <StyledTableCell>
                  ${Number(position.collateral || 0).toLocaleString()}
                </StyledTableCell>
              </StyledTableRow>
            ))}
            <StyledTableRow>
              <StyledTableCell sx={{ fontWeight: 700 }} colSpan={2}>
                Totals
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.value).toLocaleString()}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.collateral).toLocaleString()}
              </StyledTableCell>
            </StyledTableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </MainCard>
  );
};

export default PortfolioTableCard;
