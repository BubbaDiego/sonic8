import { useState, useMemo } from 'react';
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
  TableRow,
  Box
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { tableCellClasses } from '@mui/material/TableCell';
import MainCard from 'ui-component/cards/MainCard';
import { useGetPositions } from 'api/positions';

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

const PositionsTableCard = () => {
  const { positions = [] } = useGetPositions();
  const [orderBy, setOrderBy] = useState('asset_type');
  const [order, setOrder] = useState('asc');

  const sorted = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aVal = a[orderBy];
      const bVal = b[orderBy];
      if (order === 'asc') {
        return aVal < bVal ? -1 : 1;
      }
      return bVal < aVal ? -1 : 1;
    });
  }, [positions, order, orderBy]);

  const totals = useMemo(() => {
    const totalValue = positions.reduce((sum, p) => sum + parseFloat(p.value || 0), 0);
    const totalCollateral = positions.reduce((sum, p) => sum + parseFloat(p.collateral || 0), 0);
    return { value: totalValue, collateral: totalCollateral };
  }, [positions]);

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
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
              {[
                'wallet_name',
                'asset_type',
                'position_type',
                'size',
                'value',
                'collateral',
                'travel_percent',
                'liquidation_distance',
                'heat_index'
              ].map((col) => (
                <StyledTableCell key={col}>
                  <TableSortLabel
                    active={orderBy === col}
                    direction={orderBy === col ? order : 'asc'}
                    onClick={() => handleSort(col)}
                  >
                    {col === 'wallet_name'
                      ? 'Wallet'
                      : col
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (l) => l.toUpperCase())}
                  </TableSortLabel>
                </StyledTableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.map((position) => (
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
                <StyledTableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Avatar
                      src={`/static/images/${(position.asset_type || 'unknown')
                        .toLowerCase()}_logo.png`}
                      alt={position.asset_type}
                      sx={{ width: 24, height: 24, mr: 1 }}
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = '/static/images/unknown.png';
                      }}
                    />
                    {position.asset_type}
                  </Box>
                </StyledTableCell>
                <StyledTableCell>{position.position_type}</StyledTableCell>
                <StyledTableCell>{position.size}</StyledTableCell>
                <StyledTableCell>
                  ${Number(position.value || 0).toLocaleString()}
                </StyledTableCell>
                <StyledTableCell>
                  ${Number(position.collateral || 0).toLocaleString()}
                </StyledTableCell>
                <StyledTableCell>{`${Number(position.travel_percent || 0).toFixed(2)}%`}</StyledTableCell>
                <StyledTableCell>{Number(position.liquidation_distance || 0).toFixed(2)}</StyledTableCell>
                <StyledTableCell>{Number(position.heat_index || 0).toFixed(2)}</StyledTableCell>
              </StyledTableRow>
            ))}
            <StyledTableRow>
              <StyledTableCell sx={{ fontWeight: 700 }} colSpan={7}>
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

export default PositionsTableCard;

