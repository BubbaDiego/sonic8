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
  TableRow,
  Grid
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { tableCellClasses } from '@mui/material/TableCell';
import MainCard from 'ui-component/cards/MainCard';
import axios from 'utils/axios';

import ValueToCollateralChartCard from './ValueToCollateralChartCard';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import TotalHeatIndexDarkCard from 'ui-component/cards/TotalHeatIndexDarkCard';
import TotalHeatIndexLightCard from 'ui-component/cards/TotalHeatIndexLightCard';
import TotalSizeDarkCard from 'ui-component/cards/TotalSizeDarkCard';
import TotalSizeLightCard from 'ui-component/cards/TotalSizeLightCard';
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';
import UserCountCard from 'ui-component/cards/UserCountCard';
import SizeHedgeChartCard from './SizeHedgeChartCard';

import { gridSpacing } from 'store/constant';

import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import AccountCircleTwoTone from '@mui/icons-material/AccountCircleTwoTone';
import DescriptionTwoToneIcon from '@mui/icons-material/DescriptionTwoTone';

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

  useEffect(() => {
    async function loadPositions() {
      try {
        const response = await axios.get('/positions');
        const data = Array.isArray(response.data) ? response.data : [];
        setPositions(data);
        const totalValue = data.reduce((sum, p) => sum + parseFloat(p.value || 0), 0);
        const totalCollateral = data.reduce((sum, p) => sum + parseFloat(p.collateral || 0), 0);
        setTotals({ value: totalValue, collateral: totalCollateral });
      } catch (e) {
        console.error(e);
        setPositions([]);
        setTotals({ value: 0, collateral: 0 });
      }
    }
    loadPositions();
  }, []);

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
                <StyledTableCell key={col}>{col.charAt(0).toUpperCase() + col.slice(1)}</StyledTableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.length > 0 ? positions.map((position) => (
              <StyledTableRow hover key={position.id}>
                <StyledTableCell>{position.wallet_name}</StyledTableCell>
                <StyledTableCell>{position.asset_type}</StyledTableCell>
                <StyledTableCell>{position.size}</StyledTableCell>
                <StyledTableCell>${Number(position.value || 0).toLocaleString()}</StyledTableCell>
                <StyledTableCell>${Number(position.collateral || 0).toLocaleString()}</StyledTableCell>
              </StyledTableRow>
            )) : (
              <StyledTableRow>
                <StyledTableCell colSpan={5}>No data available</StyledTableCell>
              </StyledTableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </MainCard>
  );
};

export default function Sonic() {
  const { mode } = useConfig();

  const LeverageCard = mode === ThemeMode.DARK ? TotalLeverageDarkCard : TotalLeverageLightCard;
  const HeatIndexCard = mode === ThemeMode.DARK ? TotalHeatIndexDarkCard : TotalHeatIndexLightCard;
  const SizeCard = mode === ThemeMode.DARK ? TotalSizeDarkCard : TotalSizeLightCard;

  return (
    <Grid container spacing={gridSpacing}>
      <Grid item xs={12} md={8}>
        <PortfolioTableCard />
      </Grid>
      <Grid item xs={12} md={4}>
        <ValueToCollateralChartCard />
      </Grid>
      <Grid item xs={12} md={4}>
        <TotalValueCard primary="Total Value" secondary="$0" content="1000 Shares" iconPrimary={MonetizationOnTwoToneIcon} color="secondary.main" />
      </Grid>
      <Grid item xs={12} md={4}>
        <LeverageCard isLoading={false} />
      </Grid>
      <Grid item xs={12} md={4}>
        <HeatIndexCard isLoading={false} />
      </Grid>
      <Grid item xs={12} md={4}>
        <SizeCard isLoading={false} />
      </Grid>
      <Grid item xs={12} md={8}>
        <SizeHedgeChartCard />
      </Grid>
    </Grid>
  );
}
