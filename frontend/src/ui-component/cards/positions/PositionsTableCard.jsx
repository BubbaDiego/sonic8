import { useState, useMemo } from 'react';
import {
  Avatar,
  Table,
  TableBody,
  TableHead,
  TableSortLabel,
  Typography,
  TableCell,
  TableRow,
  Box
} from '@mui/material';
import FullWidthPaper from 'ui-component/cards/FullWidthPaper';
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
    let totalSize = 0;
    let totalValue = 0;
    let totalCollateral = 0;
    let weightedTravel = 0;
    let weightedLiqDist = 0;
    let weightedHeat = 0;
    let totalWeight = 0;

    positions.forEach((p) => {
      const size = parseFloat(p.size || 0);
      const value = parseFloat(p.value || 0);
      const collateral = parseFloat(p.collateral || 0);
      const travel = parseFloat(p.travel_percent || 0);
      const liq = parseFloat(p.liquidation_distance || 0);
      const heat = parseFloat(p.heat_index || 0);

      totalSize += size;
      totalValue += value;
      totalCollateral += collateral;
      const weight = size || 1;
      weightedTravel += travel * weight;
      weightedLiqDist += liq * weight;
      weightedHeat += heat * weight;
      totalWeight += weight;
    });

    const avgTravel = totalWeight ? weightedTravel / totalWeight : 0;
    const avgLiqDist = totalWeight ? weightedLiqDist / totalWeight : 0;
    const avgHeat = totalWeight ? weightedHeat / totalWeight : 0;

    return {
      size: totalSize,
      value: totalValue,
      collateral: totalCollateral,
      travel: avgTravel,
      liqDist: avgLiqDist,
      heat: avgHeat
    };
  }, [positions]);

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  return (
    <MainCard sx={{ width: '100%' }}>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Portfolio Positions
      </Typography>
      <FullWidthPaper>
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
                    src={`/images/${(position.wallet_name || 'unknown')
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
                      src={`/images/${(position.asset_type || 'unknown')
                        .toLowerCase()}_logo.png`}
                      alt={position.asset_type}
                      sx={{ width: 24, height: 24, mr: 1 }}
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = '/images/unknown.png';
                      }}
                    />
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
              <StyledTableCell sx={{ fontWeight: 700 }}>Totals</StyledTableCell>
              <StyledTableCell />
              <StyledTableCell />
              <StyledTableCell sx={{ fontWeight: 700 }}>
                {Number(totals.size).toLocaleString()}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.value).toLocaleString()}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                ${Number(totals.collateral).toLocaleString()}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                {`${Number(totals.travel).toFixed(2)}%`}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                {Number(totals.liqDist).toFixed(2)}
              </StyledTableCell>
              <StyledTableCell sx={{ fontWeight: 700 }}>
                {Number(totals.heat).toFixed(2)}
              </StyledTableCell>
            </StyledTableRow>
          </TableBody>
        </Table>
      </FullWidthPaper>
    </MainCard>
  );
};

export default PositionsTableCard;

